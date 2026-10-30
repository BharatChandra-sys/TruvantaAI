"""
Claim memory for the live check.

Every finished check is stored in pgvector (fact_checks, evidence_documents,
fact_check_evidence). Before searching, the live check asks the memory for a
past, well-sourced check that says the same thing; a confident match answers
at once with the sources found then. Unlike the response cache this survives
restarts and deploys, and it matches rewordings, not only identical text.

Embeddings barely see word order or small words: "Light travels faster than
sound" and its reverse score 0.966. So memory works in two tiers:

  instant  the same content words in the same order (only filler words and
           plurals differ), same negations and numbers, a recent check, and
           a verdict that sources backed and that two independent checks
           reached (one check can be a model's misreading; a disagreeing
           check marks it disputed). The stored answer is returned.
  related  any similar past check. Its stored sources join the live search
           results as passages, and the model judges them against the claim
           in front of it, so a reworded or reversed claim is still read
           correctly. This is the RAG step, and it keeps checks working when
           live search comes back thin.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from datetime import datetime, timedelta
from typing import Optional

from app.retrieval.embeddings import embed, embed_batch, to_pgvector

logger = logging.getLogger(__name__)

MEMORY_ENABLED = os.getenv("MEMORY_ENABLED", "true").lower() != "false"
# Similarity thresholds depend on the embedding model (embeddings.thresholds());
# these override them when set.
_MATCH_OVERRIDE = os.getenv("MEMORY_MATCH_SIMILARITY")
_RELATED_OVERRIDE = os.getenv("MEMORY_RELATED_SIMILARITY")


def _thresholds():
    from app.retrieval.embeddings import thresholds
    t = thresholds()
    return (float(_MATCH_OVERRIDE) if _MATCH_OVERRIDE else t["match"],
            float(_RELATED_OVERRIDE) if _RELATED_OVERRIDE else t["related"])


def _space() -> str:
    """Tag for stored rows: vectors only compare with vectors from the same model."""
    from app.retrieval.embeddings import model_id
    return f"stream|{model_id()}"
MAX_RELATED_PASSAGES = 3
# Independent checks that must agree before a stored verdict answers instantly.
CONFIRMATIONS_FOR_INSTANT = int(os.getenv("MEMORY_CONFIRMATIONS", "2"))
# Agreeing checks count as independent only this far apart. Re-checking a claim
# minutes later mostly re-reads the same sources with the same model, so it would
# let one misreading confirm itself.
CONFIRM_GAP_HOURS = float(os.getenv("MEMORY_CONFIRM_GAP_HOURS", "12"))
MAX_AGE_DAYS = int(os.getenv("MEMORY_MAX_AGE_DAYS", "30"))
_CANDIDATES = 5

_WORD = re.compile(r"[a-z0-9']+")
# Standalone quantities only (2016, 3.5, 1,000): digits joined to letters or hyphens
# are parts of names ("5G", "COVID-19", "R-37M"), not numbers a claim turns on.
_NUMBER = re.compile(r"(?<![\w-])\d+(?:[.,]\d+)*(?![\w-])")
_NEGATIONS = {"not", "no", "never", "none", "nobody", "nothing", "neither", "nor",
              "cannot", "without", "isn't", "aren't", "wasn't", "weren't", "doesn't",
              "don't", "didn't", "won't", "can't", "hasn't", "haven't", "hadn't"}


def claim_key(claim: str) -> str:
    """Hash of the claim's words, so case, spacing and punctuation don't create duplicates."""
    words = _WORD.findall(claim.lower())
    return hashlib.sha256(" ".join(words).encode()).hexdigest()


def _signature(text: str):
    t = text.lower().replace("’", "'")
    words = _WORD.findall(t)
    negations = sum(1 for w in words if w in _NEGATIONS or w.endswith("n't"))
    return negations % 2, frozenset(n.replace(",", "") for n in _NUMBER.findall(t))


_FILLER = {"a", "an", "the", "is", "are", "was", "were", "be", "been", "of", "to", "in", "on",
           "at", "by", "for", "with", "from", "that", "this", "it", "its", "and", "or", "as",
           "do", "does", "did", "has", "have", "had", "having", "being", "will", "would", "can",
           "very", "really", "actually", "indeed"}


def _content_words(text: str) -> list:
    words = _WORD.findall(text.lower().replace("’", "'"))
    return [w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
            for w in words if w not in _FILLER]


def same_meaning(a: str, b: str) -> bool:
    """Guards a vector match: same negation polarity and the same numbers."""
    return _signature(a) == _signature(b)


def same_wording(a: str, b: str) -> bool:
    """Same content words in the same order, so the stored answer applies as is."""
    return same_meaning(a, b) and _content_words(a) == _content_words(b)


def _session():
    from database import SessionLocal, is_sqlite
    return None if is_sqlite else SessionLocal()


# The lookup sits beside the live search, so it must cost as few round trips
# as possible: a database far from the server costs ~250 ms per trip. Reads
# use their own small autocommit pool with no ping on checkout (no BEGIN, no
# ROLLBACK, no SELECT 1), and send the settings and the query as one batch.
_read_engine = None
_NEAREST_SQL = """
    SET ivfflat.probes = 100;
    SET hnsw.ef_search = 100;
    SELECT claim_text, verdict, confidence, verification_status, rag_assessment, updated_at,
           1 - (embedding <=> CAST(%(vec)s AS halfvec)) AS similarity
    FROM fact_checks
    WHERE embedding IS NOT NULL
      AND model_version = %(space)s
      AND rag_assessment IS NOT NULL
      AND updated_at >= %(since)s
    ORDER BY embedding <=> CAST(%(vec)s AS halfvec)
    LIMIT %(k)s
"""
# ivfflat.probes = 100 makes the IVFFlat index exact: built on a near-empty
# table, it otherwise probes 1 list of 100 and misses most rows. Exact search
# is cheap at this size; the HNSW migration removes the need for it.
# The query vector is cast to the column's type, halfvec, which the HNSW index is built on.


def _engine():
    global _read_engine
    if _read_engine is None:
        from database import engine, is_sqlite
        if is_sqlite:
            return None
        from sqlalchemy import create_engine
        _read_engine = create_engine(engine.url, pool_size=2, max_overflow=2, pool_pre_ping=False,
                                     pool_recycle=240, isolation_level="AUTOCOMMIT")
    return _read_engine


def warm_up() -> None:
    """Load the embedding model and open a read connection before the first check needs them."""
    import threading

    def run():
        try:
            from app.retrieval.embeddings import available
            if not (MEMORY_ENABLED and available()):
                return
            eng = _engine()
            if eng is not None:
                with eng.connect() as conn:
                    conn.exec_driver_sql("SELECT 1")
        except Exception as e:
            logger.debug("memory warm-up failed: %s", e)

    threading.Thread(target=run, daemon=True, name="memory-warmup").start()


def _nearest(vec: list) -> Optional[list]:
    eng = _engine()
    if eng is None:
        return None
    params = {"vec": to_pgvector(vec), "since": datetime.utcnow() - timedelta(days=MAX_AGE_DAYS),
              "space": _space(),
              "k": _CANDIDATES}
    for attempt in (1, 2):   # a pooled connection may have been closed while Neon slept
        try:
            with eng.connect() as conn:
                return conn.exec_driver_sql(_NEAREST_SQL, params).fetchall()
        except Exception as e:
            if attempt == 2:
                logger.debug("memory lookup failed: %s", e)
    return None


def lookup(claim: str) -> dict:
    """
    {"instant": stored result or None, "passages": related stored sources}.
    The instant result carries "memory": {claim, similarity, checked_at}.
    """
    empty = {"instant": None, "passages": []}
    if not MEMORY_ENABLED:
        return empty
    vec = embed(claim)
    if vec is None:
        return empty
    rows = _nearest(vec)
    if rows is None:
        return empty

    match_at, related_at = _thresholds()
    instant, passages, seen = None, [], set()
    for r in rows:
        if r.similarity < related_at:
            break
        try:
            stored = json.loads(r.rag_assessment)
        except (TypeError, ValueError):
            continue
        arts = stored.get("evidence_articles") or []
        trusted = (r.verification_status == "human_reviewed"
                   or (r.verification_status == "verified"
                       and stored.get("confirmations", 1) >= CONFIRMATIONS_FOR_INSTANT))
        if (instant is None and trusted and r.similarity >= match_at
                and r.verdict in ("real", "fake") and stored.get("basis") == "sources" and arts
                and same_wording(claim, r.claim_text)):
            logger.info("memory hit %.3f: %r -> %r", r.similarity, claim[:60], r.claim_text[:60])
            instant = {
                "verdict": r.verdict,
                "confidence": r.confidence,
                "explanation": stored.get("explanation", ""),
                "evidence_articles": arts,
                "evidence_score": stored.get("evidence_score"),
                "model": stored.get("model"),
                "basis": "sources",
                "memory": {"claim": r.claim_text, "similarity": round(float(r.similarity), 3),
                           "checked_at": r.updated_at.isoformat() + "Z" if r.updated_at else None},
            }
        # Sources the earlier check found relevant become passages for this one.
        for a in arts:
            if len(passages) >= MAX_RELATED_PASSAGES:
                break
            if a.get("url") in seen or a.get("model_stance") in (None, "neutral") or a.get("low_trust"):
                continue
            seen.add(a.get("url"))
            passages.append({"kind": a.get("kind") or "news", "url": a["url"], "title": a.get("title", ""),
                             "source": a.get("source", ""), "text": a.get("snippet", ""),
                             "rating": a.get("rating", ""), "published": a.get("published", ""),
                             "low_trust": False, "from_memory": True})
    # Stored sources are web text too, and rows written before the guard existed were never screened.
    from app.analysis.evidence_guard import screen
    return {"instant": instant, "passages": screen(passages)}


def _status(result: dict) -> str:
    """VERIFIED only for confident verdicts that independent, reliable sources back."""
    from app.models import VerificationStatus
    verdict = result.get("verdict")
    if result.get("basis") != "sources" or verdict not in ("real", "fake") \
            or (result.get("confidence") or 0) < 0.8:
        return VerificationStatus.MODEL_ONLY
    agree = "support" if verdict == "real" else "contradict"
    arts = result.get("evidence_articles") or []
    backing = [a for a in arts if not a.get("low_trust") and a.get("model_stance") == agree]
    against = [a for a in arts if not a.get("low_trust") and a.get("model_stance") not in (agree, "neutral", None)]
    if len(backing) >= 2 and not against:
        return VerificationStatus.VERIFIED
    return VerificationStatus.MODEL_ONLY


def confirm(old_verdict, old_status, old_confirmations, new_verdict, new_status, hours_since=None):
    """
    (status, confirmations) after a new check of a stored claim. Agreeing,
    well-sourced checks at least CONFIRM_GAP_HOURS apart add up; a firm verdict
    that contradicts the stored one disputes it; a person's review is never
    overwritten.
    """
    from app.models import VerificationStatus as VS
    if old_status == VS.HUMAN_REVIEWED:
        return VS.HUMAN_REVIEWED, old_confirmations
    if old_verdict in ("real", "fake") and new_verdict in ("real", "fake") and old_verdict != new_verdict:
        return VS.DISPUTED, 1
    if old_verdict == new_verdict and new_status == VS.VERIFIED:
        if hours_since is not None and hours_since < CONFIRM_GAP_HOURS:
            return new_status, old_confirmations or 1
        return new_status, (old_confirmations or 1) + 1
    return new_status, 1


def remember(claim: str, result: dict) -> None:
    """Store a finished check, its sources and their embeddings in one transaction."""
    if not MEMORY_ENABLED or result.get("memory") or result.get("verdict") not in ("real", "fake", "uncertain"):
        return
    arts = [a for a in (result.get("evidence_articles") or []) if a.get("url")][:8]
    # Only the claim is searched, so only it gets a vector: already computed (and
    # cached) by the lookup, so storing costs no embedding call.
    claim_vec = embed(claim)
    if claim_vec is None:
        return
    db = _session()
    if db is None:
        return
    try:
        from app.models import FactCheck, EvidenceDocument, FactCheckEvidence, vector_value
        now = datetime.utcnow()
        stored = {
            "basis": result.get("basis", "sources"),
            "explanation": result.get("explanation", ""),
            "evidence_articles": arts,
            "evidence_score": result.get("evidence_score"),
            "model": result.get("model"),
        }
        key = claim_key(claim)
        fc = db.query(FactCheck).filter(FactCheck.claim_hash == key).first()
        if fc is None:
            fc = FactCheck(claim_hash=key, claim_text=claim[:2000], created_at=now)
            db.add(fc)
        # Independent checks that reached the same firm verdict. One check alone,
        # however well sourced it looks, can be a model's misreading; a check
        # that disagrees with the stored verdict disputes it.
        try:
            previous = json.loads(fc.rag_assessment) if fc.rag_assessment else {}
        except (TypeError, ValueError):
            previous = {}
        last = previous.get("confirmed_at")
        hours = ((now - datetime.fromisoformat(last)).total_seconds() / 3600) if last else None
        status, stored["confirmations"] = confirm(
            fc.verdict, fc.verification_status, previous.get("confirmations", 1),
            result["verdict"], _status(result), hours)
        counted = stored["confirmations"] != previous.get("confirmations", 1) or not last
        stored["confirmed_at"] = now.isoformat() if counted else last

        fc.normalized_claim = " ".join(_WORD.findall(claim.lower()))[:2000]
        fc.embedding = vector_value(claim_vec)
        fc.verdict = result["verdict"]
        fc.confidence = float(result.get("confidence") or 0.5)
        fc.verification_status = status
        fc.llm_verdict = result["verdict"] if result.get("basis") == "knowledge" else None
        fc.evidence_score = result.get("evidence_score")
        fc.rag_assessment = json.dumps(stored, ensure_ascii=False)
        fc.model_version = _space()
        fc.updated_at = now
        db.flush()

        urls = [a["url"][:2048] for a in arts]
        existing = {d.url: d for d in db.query(EvidenceDocument).filter(EvidenceDocument.url.in_(urls))} if urls else {}
        links = {l.evidence_document_id: l for l in
                 db.query(FactCheckEvidence).filter(FactCheckEvidence.fact_check_id == fc.id)}
        for a in arts:
            url = a["url"][:2048]
            doc = existing.get(url)
            if doc is None:
                doc = EvidenceDocument(url=url)
                db.add(doc)
                existing[url] = doc
            doc.title = a.get("title") or doc.title
            doc.content = a.get("snippet") or doc.content
            doc.domain = (a.get("source") or "")[:256] or doc.domain
            doc.source_type = a.get("kind") or doc.source_type
            doc.trust_score = a.get("trust_score", doc.trust_score or 0.5)
            doc.source_tier = 2 if a.get("kind") in ("fact_check", "research") else 5 if a.get("low_trust") else 3
            doc.retrieved_at = now
            db.flush()
            link = links.get(doc.id)
            if link is None:
                link = FactCheckEvidence(fact_check_id=fc.id, evidence_document_id=doc.id)
                db.add(link)
                links[doc.id] = link
            link.stance = a.get("model_stance") or a.get("stance")
            link.relevance_score = 1.0 if a.get("cited") else 0.5
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning("memory write failed: %s", e)
    finally:
        db.close()
