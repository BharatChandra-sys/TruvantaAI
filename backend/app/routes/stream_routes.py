# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
"""
Real-time fact check over Server-Sent Events.

POST /check/stream streams the check as it happens instead of answering once
at the end:

  start      immediately        {"claim"}
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

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.auth import get_current_user
from app.cache import cache
from app.schemas import MessageRequest

logger = logging.getLogger(__name__)
router = APIRouter()

STREAM_CACHE_TTL = 60 * 60


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _public(item: dict) -> dict:
    """What the card needs to show a source while the check is still running."""
    return {k: item.get(k, "") for k in ("url", "title", "source", "kind", "rating")}


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


def _run(claim: str, user_id):
    from app.analysis.ai import run_ai_analysis, run_grounded_analysis
    from app.analysis.evidence import _rating_stance
    from app.analysis.search import iter_search, reconcile, to_evidence, verdict_without_model

    t0 = time.monotonic()
    cache_key = "stream:" + hashlib.sha256(" ".join(claim.lower().split()).encode()).hexdigest()
    yield _sse("start", {"claim": claim})

    cached = cache.get(cache_key)
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

        passages, factcheck_sent = [], False
        for kind, payload in iter_search(text):
            if kind == "done":
                passages = payload
                break
            yield _sse("sources", {"items": [_public(it) for it in payload]})
            if not factcheck_sent:
                fc = next((it for it in payload if it["kind"] == "fact_check"), None)
                if fc:
                    factcheck_sent = True
                    yield _sse("factcheck", {**_public(fc), "stance": _rating_stance(fc.get("rating", ""))})

        yield _sse("judging", {"count": len(passages)})
        grounded = run_grounded_analysis(text, passages)
        ev_score, _urls, articles, explanation = to_evidence(passages, grounded)

        if grounded:
            verdict = grounded["verdict"]
            confidence = 0.5 if verdict == "uncertain" else round(min(0.97, max(0.55, grounded["confidence"])), 2)
            verdict, confidence = reconcile(verdict, confidence, articles)
            ai_score, model = grounded["ai_score"], grounded.get("model")
        else:
            # No sources, or no model answered. Never fall back to the model's memory:
            # it doesn't know recent events and would answer confidently anyway.
            verdict, confidence, explanation = verdict_without_model(passages, articles)
            ai_score = {"fake": 0.85, "real": 0.15}.get(verdict, 0.5)
            model = None

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
            "grounded": bool(grounded),
        }
        if grounded or articles:
            cache.set(cache_key, result, STREAM_CACHE_TTL)
        yield _sse("verdict", result)
        yield _sse("done", {"ms": round((time.monotonic() - t0) * 1000)})
        threading.Thread(target=_persist, args=(claim, result, user_id), daemon=True,
                         name="stream-persist").start()
    except Exception as e:
        logger.exception("stream: check failed")
        yield _sse("error", {"message": "The check failed. Try again in a moment."})


@router.post("/check/stream")
def check_stream(req: MessageRequest, user=Depends(get_current_user)):
    """Signed-in users only: checks use free-tier quotas that must not be open to anyone."""
    claim = req.message.strip()
    return StreamingResponse(
        _run(claim, user.id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
