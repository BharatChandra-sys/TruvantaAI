# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
# Project: FactCheckAI � https://github.com/BharatChandra-sys/fake-news-extension
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Index, Enum
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime
import enum

# pgvector — lazy import so the module loads even without pgvector installed.
# Embeddings are stored as halfvec (16-bit floats): half the storage and index
# memory of vector, and cosine similarity moves by under 0.0001, far inside the
# smallest gap between the memory thresholds and the scores they separate.
try:
    from pgvector.sqlalchemy import HALFVEC as PGVector
    _VECTOR_AVAILABLE = True
except ImportError:
    PGVector = None
    _VECTOR_AVAILABLE = False

# Embedding dimension for all-MiniLM-L6-v2
EMBEDDING_DIM = 384


def _vector_col(dim: int = EMBEDDING_DIM):
    """Return a pgvector halfvec Column if available, else Text (serialized JSON)."""
    if _VECTOR_AVAILABLE and PGVector is not None:
        return Column(PGVector(dim), nullable=True)
    return Column(Text, nullable=True)  # fallback: store as JSON string


def vector_value(vec):
    """A vector in the form the embedding column takes: a list for pgvector, JSON text otherwise."""
    if vec is None:
        return None
    if _VECTOR_AVAILABLE and PGVector is not None:
        return list(vec)
    import json
    return json.dumps(list(vec))


class VerificationStatus(str, enum.Enum):
    MODEL_ONLY      = "model_only"       # Only ML/LLM signals, no human review
    VERIFIED        = "verified"          # High confidence + trustworthy evidence
    HUMAN_REVIEWED  = "human_reviewed"   # Explicit human correction submitted
    DISPUTED        = "disputed"          # Conflicting signals or low-trust sources


class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String, unique=True, index=True, nullable=False)
    name       = Column(String, nullable=True)
    picture    = Column(String, nullable=True)
    hashed_pw  = Column(String, nullable=True)
    google_id  = Column(String, unique=True, nullable=True, index=True)
    is_active  = Column(Boolean, default=True)
    tier       = Column(String, default="free", nullable=False)  # free, pro, enterprise
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions  = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    feedbacks = relationship("UserFeedback", back_populates="user", cascade="all, delete-orphan")


class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    id         = Column(Integer, primary_key=True, index=True)
    email      = Column(String, index=True, nullable=False)
    otp        = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    used       = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title      = Column(String, default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True)

    user     = relationship("User", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session",
                            cascade="all, delete-orphan", order_by="ChatMessage.created_at")

    __table_args__ = (
        Index("ix_chat_sessions_user_updated", "user_id", "updated_at"),
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id          = Column(Integer, primary_key=True, index=True)
    session_id  = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role        = Column(String, nullable=False)       # "user" | "assistant"
    content     = Column(Text, nullable=False)
    is_claim    = Column(Boolean, default=False)
    verdict     = Column(String, nullable=True)
    confidence  = Column(Float, nullable=True)
    ml_score    = Column(Float, nullable=True)
    ai_score    = Column(Float, nullable=True)
    explanation = Column(Text, nullable=True)
    evidence    = Column(Text, nullable=True)          # JSON string
    created_at  = Column(DateTime, default=datetime.utcnow, index=True)

    session = relationship("ChatSession", back_populates="messages")


class UserFeedback(Base):
    """Stores user corrections — predicted vs actual verdict."""
    __tablename__ = "user_feedback"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    claim_text  = Column(Text, nullable=False)
    predicted   = Column(String, nullable=False)
    actual      = Column(String, nullable=False)
    confidence  = Column(Float, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="feedbacks")


class ClaimRecord(Base):
    """Tracks every claim verification — enables temporal analysis."""
    __tablename__ = "claim_records"

    id             = Column(Integer, primary_key=True, index=True)
    user_id        = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    claim_hash     = Column(String(64), nullable=False, index=True)
    claim_text     = Column(Text, nullable=False)
    verdict        = Column(String, nullable=False, index=True)
    confidence     = Column(Float, nullable=True)
    ml_score       = Column(Float, nullable=True)
    ai_score       = Column(Float, nullable=True)
    evidence_score = Column(Float, nullable=True)
    pub_date       = Column(DateTime, nullable=True, index=True)
    created_at     = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        # Composite indexes for the most common query patterns
        Index("ix_claim_records_hash_created", "claim_hash", "created_at"),
        Index("ix_claim_records_user_created", "user_id", "created_at"),
        Index("ix_claim_records_verdict_created", "verdict", "created_at"),
    )


class VelocityRecord(Base):
    """Tracks claim velocity for rapid spread detection."""
    __tablename__ = "velocity_records"

    id                = Column(Integer, primary_key=True, index=True)
    claim_hash        = Column(String(64), nullable=False, index=True)
    claim_text        = Column(Text, nullable=False)
    velocity_score    = Column(Float, nullable=False)
    count_5min        = Column(Integer, nullable=False)
    count_1hr         = Column(Integer, nullable=False)
    count_24hr        = Column(Integer, nullable=False)
    is_viral          = Column(Boolean, default=False, index=True)
    is_trending       = Column(Boolean, default=False, index=True)
    cooldown_score    = Column(Float, nullable=True)
    cooldown_level    = Column(String, nullable=True)
    # Phase 2.5: Semantic clustering
    cluster_id        = Column(Integer, nullable=True, index=True)
    cluster_size      = Column(Integer, nullable=True)
    campaign_score    = Column(Float, nullable=True)
    is_coordinated    = Column(Boolean, default=False, index=True)
    created_at        = Column(DateTime, default=datetime.utcnow, index=True)
    # Alias so viral_routes.py can use .timestamp without breaking
    timestamp         = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_velocity_records_hash_created", "claim_hash", "created_at"),
        Index("ix_velocity_records_viral_created", "is_viral", "created_at"),
        Index("ix_velocity_records_coordinated", "is_coordinated", "created_at"),
    )


# ── Phase 4.3: A/B Testing Models ─────────────────────────────

class ABTest(Base):
    """A/B test configuration for model experimentation."""
    __tablename__ = "ab_tests"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    status      = Column(String, default="draft", index=True)  # draft, active, paused, completed
    
    # Variant configuration (JSON string)
    # Example: {"control": {"model": "v1.0"}, "treatment": {"model": "v2.0"}}
    variants    = Column(Text, nullable=False)
    
    # Traffic split (JSON string)
    # Example: {"control": 0.5, "treatment": 0.5}
    traffic_split = Column(Text, nullable=False)
    
    # Metrics to track (JSON string)
    # Example: ["accuracy", "latency", "user_trust", "sharing_reduction"]
    metrics     = Column(Text, nullable=True)
    
    # Test duration
    start_date  = Column(DateTime, nullable=True, index=True)
    end_date    = Column(DateTime, nullable=True, index=True)
    
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assignments = relationship("ABTestAssignment", back_populates="test", cascade="all, delete-orphan")
    events      = relationship("ABTestEvent", back_populates="test", cascade="all, delete-orphan")


class ABTestAssignment(Base):
    """Tracks which variant each user/session is assigned to."""
    __tablename__ = "ab_test_assignments"

    id          = Column(Integer, primary_key=True, index=True)
    test_id     = Column(Integer, ForeignKey("ab_tests.id"), nullable=False, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    session_key = Column(String, nullable=True, index=True)  # For anonymous users
    variant     = Column(String, nullable=False, index=True)  # control, treatment, etc.
    assigned_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    test = relationship("ABTest", back_populates="assignments")
    user = relationship("User")
    
    __table_args__ = (
        Index("ix_ab_assignments_test_user", "test_id", "user_id"),
        Index("ix_ab_assignments_test_session", "test_id", "session_key"),
    )


class ABTestEvent(Base):
    """Tracks events and metrics for A/B test analysis."""
    __tablename__ = "ab_test_events"

    id          = Column(Integer, primary_key=True, index=True)
    test_id     = Column(Integer, ForeignKey("ab_tests.id"), nullable=False, index=True)
    assignment_id = Column(Integer, ForeignKey("ab_test_assignments.id"), nullable=True, index=True)
    variant     = Column(String, nullable=False, index=True)
    
    # Event details
    event_type  = Column(String, nullable=False, index=True)  # prediction, feedback, share, etc.
    event_data  = Column(Text, nullable=True)  # JSON string with event-specific data
    
    # Metrics
    accuracy    = Column(Float, nullable=True)  # If feedback available
    latency_ms  = Column(Integer, nullable=True)
    confidence  = Column(Float, nullable=True)
    
    created_at  = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    test = relationship("ABTest", back_populates="events")
    assignment = relationship("ABTestAssignment")
    
    __table_args__ = (
        Index("ix_ab_events_test_variant", "test_id", "variant"),
        Index("ix_ab_events_test_type", "test_id", "event_type"),
    )


# ══════════════════════════════════════════════════════════════
# Phase 1 — Persistent Fact Memory (RAG foundation)
# ══════════════════════════════════════════════════════════════

class FactCheck(Base):
    """
    Persistent memory of every qualified fact-check result.

    Only high-confidence results with trustworthy evidence are stored
    as VERIFIED. All others are stored as MODEL_ONLY, DISPUTED, or
    HUMAN_REVIEWED. RAG retrieval prioritises VERIFIED and HUMAN_REVIEWED.

    The embedding column enables semantic (vector) search via pgvector.
    The claim_text column enables lexical (BM25) search.
    Together these support hybrid retrieval.
    """
    __tablename__ = "fact_checks"

    id                  = Column(Integer, primary_key=True, index=True)
    claim_hash          = Column(String(64), unique=True, nullable=False, index=True)
    claim_text          = Column(Text, nullable=False)
    normalized_claim    = Column(Text, nullable=True)
    embedding           = _vector_col()                  # 384-dim, all-MiniLM-L6-v2

    # Final decision
    verdict             = Column(String(16), nullable=False, index=True)  # real/fake/uncertain
    confidence          = Column(Float, nullable=False)
    verification_status = Column(String(20),
                                 default=VerificationStatus.MODEL_ONLY,
                                 nullable=False, index=True)

    # Individual signal scores (kept for meta-model retraining)
    ml_score_a          = Column(Float, nullable=True)   # RoBERTa model-a
    ml_score_b          = Column(Float, nullable=True)   # RoBERTa model-b
    tfidf_score         = Column(Float, nullable=True)
    llm_verdict         = Column(String(16), nullable=True)
    llm_confidence      = Column(Float, nullable=True)
    evidence_score      = Column(Float, nullable=True)
    manipulation_score  = Column(Float, nullable=True)
    rag_assessment      = Column(Text, nullable=True)    # JSON — RAG structured output

    # Metadata for temporal reasoning and source ranking
    language            = Column(String(8), default="en", index=True)
    topic               = Column(String(64), nullable=True, index=True)
    entities            = Column(Text, nullable=True)    # JSON list
    model_version       = Column(String(32), nullable=True)

    created_at          = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at          = Column(DateTime, default=datetime.utcnow,
                                 onupdate=datetime.utcnow)

    evidence_links      = relationship("FactCheckEvidence", back_populates="fact_check",
                                       cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_fact_checks_verdict_status", "verdict", "verification_status"),
        Index("ix_fact_checks_topic_created", "topic", "created_at"),
    )


class EvidenceDocument(Base):
    """
    Persistent evidence corpus — news articles, official publications, fact-check sources.

    The embedding enables semantic retrieval. url is unique so the same article
    is never inserted twice. Stance and trust_score enable evidence-aware retrieval
    (retrieve supporting vs contradicting evidence separately).

    source_tier implements the 5-tier source hierarchy from the plan:
      1 = official/government, 2 = research/institutional, 3 = reputable news,
      4 = secondary websites, 5 = social/unknown
    """
    __tablename__ = "evidence_documents"

    id           = Column(Integer, primary_key=True, index=True)
    url          = Column(String(2048), unique=True, nullable=False, index=True)
    title        = Column(Text, nullable=True)
    content      = Column(Text, nullable=True)
    domain       = Column(String(256), nullable=True, index=True)
    embedding    = _vector_col()                          # 384-dim

    stance       = Column(String(16), nullable=True, index=True)  # support/contradict/neutral
    trust_score  = Column(Float, default=0.5)
    bias_label   = Column(String(32), nullable=True)
    source_tier  = Column(Integer, default=4, index=True)         # 1 (best) to 5 (worst)
    source_type  = Column(String(32), nullable=True)               # news/research/factcheck/gov

    # Temporal fields for temporal reasoning
    published_at = Column(DateTime, nullable=True, index=True)
    retrieved_at = Column(DateTime, default=datetime.utcnow, index=True)

    fact_check_links = relationship("FactCheckEvidence", back_populates="evidence_document")

    __table_args__ = (
        Index("ix_evidence_stance_tier", "stance", "source_tier"),
        Index("ix_evidence_domain_published", "domain", "published_at"),
    )


class FactCheckEvidence(Base):
    """
    Many-to-many join between FactCheck and EvidenceDocument with scores.

    relevance_score is set by the cross-encoder reranker.
    stance is the cross-encoder's per-claim-evidence stance
    (may differ from the document's global stance).
    """
    __tablename__ = "fact_check_evidence"

    id                  = Column(Integer, primary_key=True, index=True)
    fact_check_id       = Column(Integer, ForeignKey("fact_checks.id"),
                                 nullable=False, index=True)
    evidence_document_id = Column(Integer, ForeignKey("evidence_documents.id"),
                                  nullable=False, index=True)
    relevance_score     = Column(Float, nullable=True)
    stance              = Column(String(16), nullable=True)  # claim-specific stance

    fact_check        = relationship("FactCheck", back_populates="evidence_links")
    evidence_document = relationship("EvidenceDocument", back_populates="fact_check_links")

    __table_args__ = (
        Index("ix_fce_fact_check_id", "fact_check_id"),
        Index("ix_fce_evidence_id", "evidence_document_id"),
    )
