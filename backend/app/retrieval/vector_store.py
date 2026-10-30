"""
Vector Store Repository

Handles:
- Upsert of FactCheck and EvidenceDocument records with embeddings
- Vector similarity search (pgvector cosine) with metadata filtering
- Lexical search fallback (BM25) when pgvector unavailable

Implements the persistence layer for semantic clustering migration:
  OLD: semantic_clustering.py → Python dict (lost on restart)
  NEW: vector_store.py → PostgreSQL + pgvector (persistent)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import (
    FactCheck,
    EvidenceDocument,
    FactCheckEvidence,
    VerificationStatus,
    EMBEDDING_DIM,
    vector_value,
)
from app.retrieval.embeddings import embed, to_pgvector

logger = logging.getLogger(__name__)

# Minimum confidence + evidence score to qualify for VERIFIED status
_VERIFIED_CONFIDENCE_THRESHOLD = 0.82
_VERIFIED_EVIDENCE_THRESHOLD   = 0.55


# ── FactCheck upsert ──────────────────────────────────────────

def upsert_fact_check(
    db:    Session,
    *,
    claim_hash:          str,
    claim_text:          str,
    verdict:             str,
    confidence:          float,
    ml_score_a:          Optional[float] = None,
    ml_score_b:          Optional[float] = None,
    tfidf_score:         Optional[float] = None,
    llm_verdict:         Optional[str]   = None,
    llm_confidence:      Optional[float] = None,
    evidence_score:      Optional[float] = None,
    manipulation_score:  Optional[float] = None,
    rag_assessment:      Optional[dict]  = None,
    language:            str             = "en",
    topic:               Optional[str]   = None,
    entities:            Optional[list]  = None,
    model_version:       Optional[str]   = None,
    human_reviewed:      bool            = False,
) -> FactCheck:
    """
    Insert or update a FactCheck record.

    Verification status is assigned automatically:
    - HUMAN_REVIEWED if human_reviewed=True
    - VERIFIED if confidence >= 0.82 AND evidence_score >= 0.55
    - MODEL_ONLY otherwise
    """
    # Determine verification status
    if human_reviewed:
        status = VerificationStatus.HUMAN_REVIEWED
    elif (confidence >= _VERIFIED_CONFIDENCE_THRESHOLD
          and evidence_score is not None
          and evidence_score >= _VERIFIED_EVIDENCE_THRESHOLD):
        status = VerificationStatus.VERIFIED
    else:
        status = VerificationStatus.MODEL_ONLY

    # Generate embedding (cached in Redis)
    try:
        embedding_vec = embed(claim_text)
        embedding_str = vector_value(embedding_vec)
    except Exception as e:
        logger.warning("Embedding failed for fact_check: %s", e)
        embedding_str = None

    existing = db.query(FactCheck).filter(
        FactCheck.claim_hash == claim_hash
    ).first()

    if existing:
        # Update signals — keep highest status
        existing.verdict            = verdict
        existing.confidence         = confidence
        existing.verification_status = (
            status
            if _status_rank(status) > _status_rank(existing.verification_status)
            else existing.verification_status
        )
        existing.ml_score_a         = ml_score_a
        existing.ml_score_b         = ml_score_b
        existing.tfidf_score        = tfidf_score
        existing.llm_verdict        = llm_verdict
        existing.llm_confidence     = llm_confidence
        existing.evidence_score     = evidence_score
        existing.manipulation_score = manipulation_score
        if rag_assessment:
            existing.rag_assessment = json.dumps(rag_assessment)
        existing.updated_at         = datetime.utcnow()
        if embedding_str:
            existing.embedding      = embedding_str
        db.commit()
        db.refresh(existing)
        return existing

    fc = FactCheck(
        claim_hash         = claim_hash,
        claim_text         = claim_text[:2000],
        embedding          = embedding_str,
        verdict            = verdict,
        confidence         = confidence,
        verification_status= status,
        ml_score_a         = ml_score_a,
        ml_score_b         = ml_score_b,
        tfidf_score        = tfidf_score,
        llm_verdict        = llm_verdict,
        llm_confidence     = llm_confidence,
        evidence_score     = evidence_score,
        manipulation_score = manipulation_score,
        rag_assessment     = json.dumps(rag_assessment) if rag_assessment else None,
        language           = language,
        topic              = topic,
        entities           = json.dumps(entities) if entities else None,
        model_version      = model_version,
    )
    db.add(fc)
    db.commit()
    db.refresh(fc)
    return fc


def _status_rank(status: str) -> int:
    return {
        VerificationStatus.MODEL_ONLY:     0,
        VerificationStatus.DISPUTED:       1,
        VerificationStatus.VERIFIED:       2,
        VerificationStatus.HUMAN_REVIEWED: 3,
    }.get(status, 0)


# ── EvidenceDocument upsert ───────────────────────────────────

def upsert_evidence(
    db: Session,
    *,
    url:          str,
    title:        Optional[str]      = None,
    content:      Optional[str]      = None,
    domain:       Optional[str]      = None,
    stance:       Optional[str]      = None,
    trust_score:  float              = 0.5,
    bias_label:   Optional[str]      = None,
    source_tier:  int                = 4,
    source_type:  Optional[str]      = None,
    published_at: Optional[datetime] = None,
) -> EvidenceDocument:
    """Insert or update an EvidenceDocument with its embedding."""
    embed_text = f"{title or ''} {content[:500] if content else ''}".strip()
    try:
        vec = embed(embed_text) if embed_text else None
        embedding_str = vector_value(vec)
    except Exception:
        embedding_str = None

    existing = db.query(EvidenceDocument).filter(
        EvidenceDocument.url == url[:2048]
    ).first()

    if existing:
        if title:    existing.title    = title
        if content:  existing.content  = content[:10000]
        if stance:   existing.stance   = stance
        existing.trust_score  = trust_score
        existing.source_tier  = source_tier
        existing.retrieved_at = datetime.utcnow()
        if embedding_str:
            existing.embedding = embedding_str
        db.commit()
        db.refresh(existing)
        return existing

    doc = EvidenceDocument(
        url          = url[:2048],
        title        = title,
        content      = content[:10000] if content else None,
        domain       = domain,
        embedding    = embedding_str,
        stance       = stance,
        trust_score  = trust_score,
        bias_label   = bias_label,
        source_tier  = source_tier,
        source_type  = source_type,
        published_at = published_at,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def link_evidence(
    db:                  Session,
    fact_check_id:       int,
    evidence_document_id: int,
    relevance_score:     Optional[float] = None,
    stance:              Optional[str]   = None,
) -> FactCheckEvidence:
    """Create a fact_check ↔ evidence_document link (idempotent)."""
    existing = db.query(FactCheckEvidence).filter(
        FactCheckEvidence.fact_check_id       == fact_check_id,
        FactCheckEvidence.evidence_document_id == evidence_document_id,
    ).first()
    if existing:
        if relevance_score is not None:
            existing.relevance_score = relevance_score
        if stance:
            existing.stance = stance
        db.commit()
        return existing

    link = FactCheckEvidence(
        fact_check_id        = fact_check_id,
        evidence_document_id = evidence_document_id,
        relevance_score      = relevance_score,
        stance               = stance,
    )
    db.add(link)
    db.commit()
    return link


# ── Vector similarity search ──────────────────────────────────

def search_similar_claims(
    db:                Session,
    claim_text:        str,
    top_k:             int   = 10,
    min_confidence:    float = 0.0,
    verification_filter: Optional[list[str]] = None,
) -> list[dict]:
    """
    Find similar historical fact-checks using cosine similarity.

    Tries pgvector operator first; falls back to Python cosine similarity
    over a recent window if pgvector is not available.

    Args:
        claim_text:            The claim to search for.
        top_k:                 Max results to return.
        min_confidence:        Only return results above this confidence.
        verification_filter:   List of VerificationStatus values to filter by.
                               Default: VERIFIED + HUMAN_REVIEWED only.
    """
    if verification_filter is None:
        verification_filter = [
            VerificationStatus.VERIFIED,
            VerificationStatus.HUMAN_REVIEWED,
        ]

    query_vec = embed(claim_text)
    if query_vec is None:
        return []

    # Try pgvector cosine distance operator (<=>)
    try:
        from sqlalchemy import text as sa_text
        vec_str = to_pgvector(query_vec)
        db.execute(sa_text("SET LOCAL ivfflat.probes = 100"))   # exact recall on small tables
        rows = db.execute(
            sa_text("""
                SELECT id, claim_text, verdict, confidence, verification_status,
                       evidence_score, manipulation_score,
                       1 - (embedding <=> :vec) AS similarity
                FROM fact_checks
                WHERE verification_status = ANY(:statuses)
                  AND confidence >= :min_conf
                  AND embedding IS NOT NULL
                ORDER BY embedding <=> :vec
                LIMIT :k
            """),
            {
                "vec":      vec_str,
                "statuses": verification_filter,
                "min_conf": min_confidence,
                "k":        top_k,
            },
        ).fetchall()

        return [
            {
                "id":                  r.id,
                "claim_text":          r.claim_text,
                "verdict":             r.verdict,
                "confidence":          r.confidence,
                "verification_status": r.verification_status,
                "evidence_score":      r.evidence_score,
                "manipulation_score":  r.manipulation_score,
                "similarity":          round(float(r.similarity), 4),
                "retrieval_method":    "pgvector",
            }
            for r in rows
        ]

    except Exception as e:
        logger.debug("pgvector search failed, using Python fallback: %s", e)

    # Python fallback — scan last 2000 records
    from app.retrieval.embeddings import cosine_similarity
    records = (
        db.query(FactCheck)
        .filter(
            FactCheck.verification_status.in_(verification_filter),
            FactCheck.confidence >= min_confidence,
            FactCheck.embedding.isnot(None),
        )
        .order_by(FactCheck.created_at.desc())
        .limit(2000)
        .all()
    )

    scored = []
    for r in records:
        try:
            stored_vec = json.loads(r.embedding)
            sim = cosine_similarity(query_vec, stored_vec)
            scored.append((sim, r))
        except Exception:
            continue

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "id":                  r.id,
            "claim_text":          r.claim_text,
            "verdict":             r.verdict,
            "confidence":          r.confidence,
            "verification_status": r.verification_status,
            "evidence_score":      r.evidence_score,
            "manipulation_score":  r.manipulation_score,
            "similarity":          round(sim, 4),
            "retrieval_method":    "python_cosine",
        }
        for sim, r in scored[:top_k]
    ]


def search_evidence(
    db:          Session,
    claim_text:  str,
    stance:      Optional[str] = None,
    top_k:       int           = 8,
    max_tier:    int           = 3,
) -> list[dict]:
    """
    Find relevant evidence documents using vector similarity.

    Args:
        stance:   Filter by stance ('support', 'contradict', 'neutral', or None for all)
        max_tier: Only return sources up to this tier (1=best, 5=worst)
    """
    query_vec = embed(claim_text)
    if query_vec is None:
        return []

    try:
        from sqlalchemy import text as sa_text
        vec_str = to_pgvector(query_vec)
        db.execute(sa_text("SET LOCAL ivfflat.probes = 100"))   # exact recall on small tables
        stance_filter = f"AND stance = :stance" if stance else ""
        rows = db.execute(
            sa_text(f"""
                SELECT id, url, title, domain, stance, trust_score, source_tier,
                       published_at,
                       1 - (embedding <=> :vec) AS similarity
                FROM evidence_documents
                WHERE source_tier <= :max_tier
                  AND embedding IS NOT NULL
                  {stance_filter}
                ORDER BY embedding <=> :vec
                LIMIT :k
            """),
            {
                "vec":      vec_str,
                "max_tier": max_tier,
                "stance":   stance,
                "k":        top_k,
            },
        ).fetchall()

        return [
            {
                "id":           r.id,
                "url":          r.url,
                "title":        r.title,
                "domain":       r.domain,
                "stance":       r.stance,
                "trust_score":  r.trust_score,
                "source_tier":  r.source_tier,
                "published_at": r.published_at.isoformat() if r.published_at else None,
                "similarity":   round(float(r.similarity), 4),
            }
            for r in rows
        ]
    except Exception as e:
        logger.debug("Evidence vector search failed: %s", e)
        return []
