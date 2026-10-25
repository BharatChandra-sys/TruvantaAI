"""Self-healing model selection: ranking, holds, recovery and rediscovery."""
import time

import pytest
import requests

from app.analysis import model_registry as mr
from app.analysis.model_registry import ModelCallError, ModelRegistry, capability_rank, try_models


@pytest.fixture
def reg(monkeypatch):
    r = ModelRegistry()
    monkeypatch.setattr(mr, "registry", r)
    return r


def test_capability_rank_prefers_bigger_and_newer():
    assert capability_rank("openai/gpt-oss-120b") > capability_rank("openai/gpt-oss-20b")
    assert capability_rank("gemini-3.7-flash") > capability_rank("gemini-3.5-flash")
    assert capability_rank("gemini-3.1-pro") > capability_rank("gemini-3.1-flash-lite")
    assert capability_rank("llama-3.3-70b-versatile") > capability_rank("llama-3.1-8b-instant")


def test_untested_models_ordered_by_capability(reg):
    assert reg.ranked("groq", ["small-7b", "big-120b", "mid-20b"]) == ["big-120b", "mid-20b", "small-7b"]


def test_working_model_moves_ahead_of_untested(reg):
    reg.report_success("groq", "mid-20b", 1.2)
    assert reg.ranked("groq", ["big-120b", "mid-20b"])[0] == "mid-20b"


def test_decommissioned_model_is_held_and_triggers_rediscovery(reg):
    refreshed = []
    reg.on_permanent_failure(refreshed.append)
    kind = reg.report_failure("groq", "old-70b", ModelCallError(400, "The model `old-70b` has been decommissioned"))
    assert kind == "permanent"
    assert "old-70b" not in reg.ranked("groq", ["old-70b", "new-20b"])
    assert refreshed == ["groq"]


def test_rate_limit_backs_off_then_recovers(reg, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(mr.time, "time", lambda: now[0])
    assert reg.report_failure("groq", "m-20b", ModelCallError(429, "rate limited")) == "transient"
    assert reg.ranked("groq", ["m-20b"]) == []
    now[0] += mr.TRANSIENT_BASE_S + 1
    assert reg.ranked("groq", ["m-20b"]) == ["m-20b"]          # automatically retried
    reg.report_failure("groq", "m-20b", ModelCallError(503, "busy"))
    now[0] += mr.TRANSIENT_BASE_S + 1
    assert reg.ranked("groq", ["m-20b"]) == []                  # second strike waits longer
    now[0] += mr.TRANSIENT_BASE_S * 2
    assert reg.ranked("groq", ["m-20b"]) == ["m-20b"]


def test_rejected_key_holds_whole_provider(reg):
    reg.report_failure("openrouter", "any", ModelCallError(401, "invalid key"))
    assert not reg.provider_available("openrouter")
    assert reg.ranked("openrouter", ["a", "b"]) == []
    assert reg.provider_available("groq")


def test_timeout_is_transient(reg):
    assert reg.report_failure("groq", "m", requests.Timeout()) == "transient"


def test_bad_output_needs_repeated_failures_before_hold(reg):
    for _ in range(mr.SOFT_FAILS_BEFORE_COOLDOWN - 1):
        assert reg.report_failure("groq", "m", ValueError("No JSON found")) == "soft"
        assert reg.ranked("groq", ["m"]) == ["m"]
    reg.report_failure("groq", "m", ValueError("No JSON found"))
    assert reg.ranked("groq", ["m"]) == []


def test_try_models_falls_through_and_learns(reg):
    calls = []

    def call(model):
        calls.append(model)
        if model == "big-120b":
            raise ModelCallError(404, "model not found")
        return {"verdict": "real"}

    result = try_models("groq", ["big-120b", "mid-20b"], call)
    assert result["verdict"] == "real" and result["_model"] == "groq:mid-20b"
    assert calls == ["big-120b", "mid-20b"]

    calls.clear()
    try_models("groq", ["big-120b", "mid-20b"], call)
    assert calls == ["mid-20b"]                                 # dead model not tried again


def test_try_models_raises_when_nothing_usable(reg):
    reg.report_failure("groq", "x", ModelCallError(401, "bad key"))
    with pytest.raises(ValueError):
        try_models("groq", ["x"], lambda m: {})


def test_snapshot_reports_health(reg):
    reg.report_success("groq", "m", 0.8)
    snap = reg.snapshot()
    assert snap["groq"]["models"]["m"]["ok"] == 1
    assert snap["groq"]["models"]["m"]["latency_s"] == 0.8
