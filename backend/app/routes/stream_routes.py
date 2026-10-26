# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
"""
Real-time fact check over Server-Sent Events.

POST /check/stream streams the check as it happens instead of answering once
at the end:

  start      immediately        {"claim"}
  early      the model's answer from established knowledge (~1 s), shown as an
             early answer while sources are read  {verdict, confidence, explanation}
  sources    as each source returns   {"items": [{url, title, source, kind, rating}]}
  factcheck  first published fact-check found (often < 1 s)  {source, rating, url, stance}
  judging    search finished, model is reading   {"count"}
  verdict    final result, same shape as /message for a claim
  done       {"ms"}
  error      {"message"}

Only the work the verdict needs is on this path; persistence happens after.
"""
import hashlib
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.auth import get_current_user_id
from app.cache import cache
from app.schemas import MessageRequest

logger = logging.getLogger(__name__)
router = APIRouter()

STREAM_CACHE_TTL = 60 * 60
# Memory lookups run beside the live search, so a miss costs nothing.
_MEMORY_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="memory")
# The early answer and the sourced verdict are model calls; they run here so the
# stream can keep sending events while they work.
_MODEL_POOL = ThreadPoolExecutor(max_workers=16, thread_name_prefix="stream-model")
_MODEL_TIMEOUT_S = 15

# How long the search waits for the lookup before starting (an instant answer
# skips it entirely), and how long to still wait once the search has ended.
_MEMORY_HEAD_START_S = 0.4
_MEMORY_GRACE_S = 0.3


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _public(item: dict) -> dict:
    """What the card needs to show a source while the check is still running."""
    out = {k: item.get(k, "") for k in ("url", "title", "source", "kind", "rating")}
    if item.get("site"):
        out["site"] = item["site"]
    return out


def _verdict_from_score(score: float):
    if score is None:
        return "uncertain", 0.5
    if score >= 0.6:
        return "fake", round(min(0.9, score), 2)
    if score <= 0.4:
        return "real", round(min(0.9, 1 - score), 2)
    return "uncertain", 0.5


def _persist(claim: str, result: dict, user_id):
    """Record the check for history and drift tracking, off the request path."""
    try:
        from database import SessionLocal
        from app.models import ClaimRecord
        session = SessionLocal()
        try:
            session.add(ClaimRecord(
                claim_hash=hashlib.sha256(claim.lower().strip().encode()).hexdigest(),
                claim_text=claim[:500],
                verdict=result["verdict"],
                confidence=result["confidence"],
                ai_score=result.get("ai_score"),
                evidence_score=result.get("evidence_score"),
                user_id=user_id,
            ))
            session.commit()
        finally:
            session.close()
    except Exception as e:
        logger.warning("stream: persistence failed: %s", e)
    try:
        from app.retrieval.memory import remember
        remember(claim, result)
    except Exception as e:
        logger.warning("stream: memory write failed: %s", e)


def _remembered(future, wait_s: float = 0.0) -> dict:
    """The memory lookup's result if it has finished (optionally waiting a little)."""
    empty = {"instant": None, "passages": []}
    if future is None:
        return empty
    try:
        return future.result(timeout=wait_s) if wait_s else (future.result() if future.done() else empty)
    except Exception:
        return empty


def _run(claim: str, user_id, fresh: bool = False):
    from app.analysis.ai import run_grounded_analysis, run_knowledge_analysis
    from app.analysis.evidence import _rating_stance
    from app.analysis.search import iter_search, reconcile, to_evidence, verdict_without_model

    t0 = time.monotonic()
    cache_key = "stream:" + hashlib.sha256(" ".join(claim.lower().split()).encode()).hexdigest()
    yield _sse("start", {"claim": claim})

    cached = None if fresh else cache.get(cache_key)
    if cached:
        yield _sse("sources", {"items": [_public(a) for a in cached.get("evidence_articles", [])]})
        yield _sse("verdict", dict(cached, cached=True))
        yield _sse("done", {"ms": round((time.monotonic() - t0) * 1000)})
        return

    try:
        text = claim
        try:
            from app.analysis.multilingual import normalize_claim
            text, _lang, _translated = normalize_claim(claim)
        except Exception as e:
            logger.debug("stream: normalization skipped: %s", e)

        try:
            from app.retrieval.memory import lookup
            recalled = None if fresh else _MEMORY_POOL.submit(lookup, text)
        except Exception as e:
            logger.debug("stream: memory unavailable: %s", e)
            recalled = None

        def answer_from_memory(hit):
            result = {"is_claim": True, "primary_claim": claim, "ai_score": None,
                      "grounded": True, **hit}
            cache.set(cache_key, result, STREAM_CACHE_TTL)
            threading.Thread(target=_persist, args=(claim, result, user_id), daemon=True,
                             name="stream-persist").start()
            return [_sse("sources", {"items": [_public(a) for a in hit["evidence_articles"]]}),
                    _sse("verdict", result),
                    _sse("done", {"ms": round((time.monotonic() - t0) * 1000)})]

        remembered = _remembered(recalled, _MEMORY_HEAD_START_S)["instant"]
        if remembered:
            yield from answer_from_memory(remembered)
            return

        # Early answer: the model's established knowledge, in parallel with the
        # search. The sourced verdict replaces it; when nothing found addresses
        # the claim, it becomes the final answer, so it is never wasted.
        knowing = _MODEL_POOL.submit(run_knowledge_analysis, text)
        early_sent = []

        def early_event():
            if early_sent or not knowing.done():
                return None
            try:
                k = knowing.result()
            except Exception:
                k = None
            early_sent.append(k)
            if not k or k["verdict"] == "uncertain":
                return None
            return _sse("early", {"verdict": k["verdict"], "confidence": k["confidence"],
                                  "explanation": k["explanation"]})

        passages, factcheck_sent = [], False
        search = iter_search(text)
        for kind, payload in search:
            hit = _remembered(recalled)["instant"]
            if hit:
                search.close()
                yield from answer_from_memory(hit)
                return
            if kind == "done":
                passages = payload
                break
            ev = early_event()
            if ev:
                yield ev
            yield _sse("sources", {"items": [_public(it) for it in payload]})
            if not factcheck_sent:
                fc = next((it for it in payload if it["kind"] == "fact_check"), None)
                if fc:
                    factcheck_sent = True
                    yield _sse("factcheck", {**_public(fc), "stance": _rating_stance(fc.get("rating", ""))})

        memory = _remembered(recalled, _MEMORY_GRACE_S)
        if memory["instant"]:
            yield from answer_from_memory(memory["instant"])
            return
        # RAG: sources that earlier checks of similar claims found relevant.
        live = {p["url"] for p in passages}
        extra = [p for p in memory["passages"] if p["url"] not in live]
        if extra:
            passages = passages + extra
            yield _sse("sources", {"items": [_public(p) for p in extra]})

        yield _sse("judging", {"count": len(passages)})
        judging = _MODEL_POOL.submit(run_grounded_analysis, text, passages)
        deadline = time.monotonic() + _MODEL_TIMEOUT_S
        grounded = None
        while True:
            try:
                grounded = judging.result(timeout=0.1)
                break
            except FutureTimeout:
                ev = early_event()
                if ev:
                    yield ev
                if time.monotonic() > deadline:
                    logger.warning("stream: grounded verdict timed out")
                    break
            except Exception as e:
                logger.warning("stream: grounded verdict failed: %s", e)
                break
        ev_score, _urls, articles, explanation = to_evidence(passages, grounded)

        if grounded:
            verdict = grounded["verdict"]
            confidence = 0.5 if verdict == "uncertain" else round(min(0.97, max(0.55, grounded["confidence"])), 2)
            verdict, confidence = reconcile(verdict, confidence, articles)
            ai_score, model = grounded["ai_score"], grounded.get("model")
        else:
            # No sources, or no model answered: a published fact-check can still decide.
            verdict, confidence, explanation = verdict_without_model(passages, articles)
            ai_score = {"fake": 0.85, "real": 0.15}.get(verdict, 0.5)
            model = None

        # Answer from established knowledge, capped and labelled in the card, when
        # nothing found addresses the claim (as opposed to sources that disagree), or
        # when sources were found but no model could read them (free-tier limits).
        # The early answer already holds it, so this costs no extra call.
        basis = "sources"
        addressed = any(a.get("model_stance") in ("support", "contradict") for a in articles)
        if verdict == "uncertain" and (not addressed or not grounded):
            try:
                knowledge = knowing.result(timeout=max(0.1, deadline - time.monotonic()))
            except Exception:
                knowledge = None
            if knowledge and knowledge["verdict"] != "uncertain":
                verdict, confidence = knowledge["verdict"], knowledge["confidence"]
                explanation, ai_score, model = knowledge["explanation"], knowledge["ai_score"], knowledge["model"]
                basis = "knowledge"

        result = {
            "is_claim": True,
            "primary_claim": claim,
            "verdict": verdict,
            "confidence": confidence,
            "explanation": explanation,
            "evidence_articles": articles,
            "evidence_score": ev_score,
            "ai_score": ai_score,
            "model": model,
            "grounded": bool(grounded) and basis == "sources",
            "basis": basis,
            # Knowledge answer although sources were found: no model could read them.
            "sources_unread": basis == "knowledge" and not grounded and bool(passages),
        }
        if (grounded or articles or basis == "knowledge") and not fresh:
            cache.set(cache_key, result, STREAM_CACHE_TTL)
        yield _sse("verdict", result)
        yield _sse("done", {"ms": round((time.monotonic() - t0) * 1000)})
        if not fresh:
            threading.Thread(target=_persist, args=(claim, result, user_id), daemon=True,
                             name="stream-persist").start()
    except Exception as e:
        logger.exception("stream: check failed")
        yield _sse("error", {"message": "The check failed. Try again in a moment."})


@router.post("/check/stream")
def check_stream(req: MessageRequest, user_id: int = Depends(get_current_user_id)):
    """Signed-in users only: checks use free-tier quotas that must not be open to anyone."""
    claim = req.message.strip()
    return StreamingResponse(
        _run(claim, user_id, fresh=req.fresh),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
