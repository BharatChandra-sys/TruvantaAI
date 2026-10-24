# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
"""
Self-healing model selection.

Providers add, rename and retire models without notice, so nothing here is
hard-coded. Discovery (ai_config) supplies whatever each provider lists right
now; this registry remembers how each model actually behaved and orders the
candidates for the next call:

  1. models that worked last time        (best capability first)
  2. models not tried yet                 (best capability first)
  3. models that failed softly            (bad JSON, the odd error)

Models that failed hard are skipped until their hold expires, then retried
automatically:

  permanent  404 / decommissioned / payment / terms → 6 h hold, and discovery
             is refreshed so newly released models are picked up
  transient  429 / 5xx / timeout / connection      → 30 s, doubling to 10 min
  auth       401 / 403                              → whole provider, 30 min

Everything is in memory and thread-safe; a restart simply re-learns.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

import requests

logger = logging.getLogger(__name__)

PERMANENT_HOLD_S = 6 * 3600
AUTH_HOLD_S = 30 * 60
TRANSIENT_BASE_S = 30
TRANSIENT_MAX_S = 10 * 60
SOFT_FAILS_BEFORE_COOLDOWN = 3

_PERMANENT_HINTS = ("decommission", "does not exist", "not found", "no longer available",
                    "not supported", "terms", "accept", "payment", "quota exhausted",
                    "no provider serves", "deprecated", "invalid model")


class ModelCallError(Exception):
    """A provider answered with an HTTP error for a specific model."""

    def __init__(self, status: int, detail: str = ""):
        super().__init__(f"HTTP {status}: {detail[:200]}")
        self.status = status
        self.detail = detail


@dataclass
class _Health:
    ok: int = 0
    fails: int = 0
    soft_fails: int = 0
    last_ok: float = 0.0
    last_fail: float = 0.0
    hold_until: float = 0.0
    hold_reason: str = ""
    streak: int = 0                # consecutive transient failures (for backoff)
    latency_ewma: Optional[float] = None
    last_error: str = ""


@dataclass
class _ProviderState:
    hold_until: float = 0.0
    hold_reason: str = ""
    models: Dict[str, _Health] = field(default_factory=dict)


def capability_rank(model_id: str) -> float:
    """
    Rough "how capable is this model" score from its name alone, so a new
    release slots in without code changes. Bigger parameter counts and newer
    versions rank higher; mini/lite/nano and preview builds rank lower.
    """
    m = model_id.lower()
    score = 0.0
    params = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)b\b", m)]
    if params:
        score += min(max(params), 500) ** 0.5 * 10      # 120b → ~110, 20b → ~45, 7b → ~26
    versions = [float(x) for x in re.findall(r"(?<![\d.])(\d+\.\d+)(?![\d.]*b\b)", m)]
    if versions:
        score += max(versions) * 8
    if re.search(r"\bpro\b|-pro\b|ultra|large", m):
        score += 25
    if "flash" in m or "turbo" in m:
        score += 8
    if re.search(r"mini|lite|nano|tiny|small|-instant", m):
        score -= 20
    if "preview" in m or "exp" in m or "beta" in m:
        score -= 10
    if "thinking" in m or "reason" in m:
        score -= 5                                       # slower for a quick verdict
    return score


class ModelRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._providers: Dict[str, _ProviderState] = {}
        self._on_permanent = []           # callbacks(provider) to refresh discovery

    # ── wiring ────────────────────────────────────────────────
    def on_permanent_failure(self, callback):
        self._on_permanent.append(callback)

    def _state(self, provider: str) -> _ProviderState:
        st = self._providers.get(provider)
        if st is None:
            st = self._providers[provider] = _ProviderState()
        return st

    # ── queries ───────────────────────────────────────────────
    def provider_available(self, provider: str) -> bool:
        with self._lock:
            return self._state(provider).hold_until <= time.time()

    def ranked(self, provider: str, models: Iterable[str]) -> List[str]:
        """Candidates in the order they should be tried, held models removed."""
        now = time.time()
        with self._lock:
            st = self._state(provider)
            if st.hold_until > now:
                return []
            ready = []
            for idx, m in enumerate(dict.fromkeys(models)):
                h = st.models.get(m)
                if h and h.hold_until > now:
                    continue
                if h and h.last_ok and h.last_ok >= h.last_fail:
                    bucket = 0                     # worked last time
                elif h is None or (h.ok == 0 and h.fails == 0):
                    bucket = 1                     # untested
                else:
                    bucket = 2                     # flaky
                ready.append((bucket, -capability_rank(m), idx, m))
            ready.sort()
            return [m for *_, m in ready]

    def snapshot(self) -> dict:
        """Current health of every model seen, for logs and the status endpoint."""
        now = time.time()
        out = {}
        with self._lock:
            for p, st in self._providers.items():
                out[p] = {
                    "on_hold_s": max(0, round(st.hold_until - now)),
                    "hold_reason": st.hold_reason if st.hold_until > now else "",
                    "models": {
                        m: {
                            "ok": h.ok,
                            "fails": h.fails,
                            "latency_s": round(h.latency_ewma, 2) if h.latency_ewma else None,
                            "on_hold_s": max(0, round(h.hold_until - now)),
                            "hold_reason": h.hold_reason if h.hold_until > now else "",
                            "last_error": h.last_error,
                        }
                        for m, h in st.models.items()
                    },
                }
        return out

    # ── reporting ─────────────────────────────────────────────
    def report_success(self, provider: str, model: str, latency_s: float):
        with self._lock:
            st = self._state(provider)
            h = st.models.setdefault(model, _Health())
            h.ok += 1
            h.last_ok = time.time()
            h.streak = 0
            h.soft_fails = 0
            h.hold_until = 0.0
            h.latency_ewma = latency_s if h.latency_ewma is None else 0.7 * h.latency_ewma + 0.3 * latency_s
            st.hold_until = 0.0

    def report_failure(self, provider: str, model: str, error: BaseException) -> str:
        """Record a failed call and return its kind: permanent, auth, transient or soft."""
        kind, reason = self._classify(error)
        now = time.time()
        refresh = False
        with self._lock:
            st = self._state(provider)
            h = st.models.setdefault(model, _Health())
            h.fails += 1
            h.last_fail = now
            h.last_error = reason[:160]
            if kind == "auth":
                st.hold_until = now + AUTH_HOLD_S
                st.hold_reason = reason
            elif kind == "permanent":
                h.hold_until = now + PERMANENT_HOLD_S
                h.hold_reason = reason
                refresh = True
            elif kind == "transient":
                h.streak += 1
                h.hold_until = now + min(TRANSIENT_BASE_S * 2 ** (h.streak - 1), TRANSIENT_MAX_S)
                h.hold_reason = reason
            else:  # soft: answered, but unusable (e.g. no JSON)
                h.soft_fails += 1
                if h.soft_fails >= SOFT_FAILS_BEFORE_COOLDOWN:
                    h.hold_until = now + TRANSIENT_BASE_S * 4
                    h.hold_reason = "repeatedly unusable output"
                    h.soft_fails = 0
        logger.warning("model %s/%s failed (%s): %s", provider, model, kind, reason[:160])
        if refresh:
            for cb in self._on_permanent:
                try:
                    cb(provider)
                except Exception as e:  # never let a callback break the request
                    logger.debug("discovery refresh failed for %s: %s", provider, e)
        return kind

    @staticmethod
    def _classify(error: BaseException):
        if isinstance(error, ModelCallError):
            s, detail = error.status, error.detail.lower()
            if s in (401, 403):
                return "auth", f"{s} key rejected"
            if s in (402, 404, 410):
                return "permanent", f"{s} {detail[:120]}"
            if s == 400 and any(h in detail for h in _PERMANENT_HINTS):
                return "permanent", f"400 {detail[:120]}"
            if s in (408, 409, 425, 429) or s >= 500:
                return "transient", f"{s} {detail[:120]}"
            if s == 413:
                return "soft", "413 payload too large"
            return "soft", f"{s} {detail[:120]}"
        if isinstance(error, (requests.Timeout, requests.ConnectionError, TimeoutError, ConnectionError)):
            return "transient", type(error).__name__
        return "soft", f"{type(error).__name__}: {error}"


registry = ModelRegistry()


def try_models(provider: str, models: Iterable[str], call, limit: int = 3):
    """
    Call `call(model)` on the best-ranked candidates until one succeeds.
    Every outcome is reported, so the next request starts from what worked.
    """
    candidates = registry.ranked(provider, models)[:limit]
    if not candidates:
        raise ValueError(f"{provider}: no usable models right now")
    last = None
    for model in candidates:
        start = time.monotonic()
        try:
            result = call(model)
        except Exception as e:
            registry.report_failure(provider, model, e)
            last = e
            continue
        registry.report_success(provider, model, time.monotonic() - start)
        if isinstance(result, dict):
            result.setdefault("_model", f"{provider}:{model}")
        return result
    raise ValueError(f"All {provider} models failed (last: {last})")
