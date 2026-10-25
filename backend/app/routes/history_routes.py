# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
# Project: FactCheckAI � https://github.com/BharatChandra-sys/fake-news-extension
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from app.models import User, ChatSession, ChatMessage
from app.auth import get_current_user

router = APIRouter(prefix="/history", tags=["history"])


# ── Sessions ─────────────────────────────────────────────────

@router.get("/sessions")
def list_sessions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    limit = min(limit, 100)  # cap at 100
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    total = db.query(ChatSession).filter(ChatSession.user_id == user.id).count()
    return {"sessions": [_session_dict(s) for s in sessions], "total": total, "limit": limit, "offset": offset}


@router.post("/sessions")
def create_session(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = ChatSession(user_id=user.id, title="New Chat")
    db.add(session)
    db.commit()
    db.refresh(session)
    return _session_dict(session)


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = _get_session(session_id, user.id, db)
    db.delete(session)
    db.commit()
    return {"ok": True}


@router.post("/sessions/bulk-delete")
def bulk_delete_sessions(
    body: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete multiple sessions in a single request — replaces N individual DELETE calls."""
    session_ids = body.get("session_ids", [])
    if not session_ids:
        return {"deleted": 0}
    # Only delete sessions owned by this user
    deleted = (
        db.query(ChatSession)
        .filter(ChatSession.id.in_(session_ids), ChatSession.user_id == user.id)
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"deleted": deleted}


@router.patch("/sessions/{session_id}/title")
def rename_session(session_id: int, body: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    session = _get_session(session_id, user.id, db)
    session.title = body.get("title", session.title)[:80]
    db.commit()
    return _session_dict(session)


# ── Messages ─────────────────────────────────────────────────

@router.get("/sessions/{session_id}/messages")
def get_messages(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
):
    _get_session(session_id, user.id, db)
    limit = min(limit, 200)
    msgs = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at, ChatMessage.id)
        .offset(offset)
        .limit(limit)
        .all()
    )
    total = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).count()
    return {"messages": [_msg_dict(m) for m in msgs], "total": total, "limit": limit, "offset": offset}


# ── Internal helper used by message route ────────────────────

def save_message(db: Session, session_id: int, role: str, content: str, extra: dict = None):
    extra = extra or {}
    msg = ChatMessage(
        session_id  = session_id,
        role        = role,
        content     = content,
        is_claim    = extra.get("is_claim", False),
        verdict     = extra.get("verdict"),
        confidence  = extra.get("confidence"),
        ml_score    = extra.get("ml_score"),
        ai_score    = extra.get("ai_score"),
        explanation = extra.get("explanation"),
        # Keep the full article objects (title / source / url) when we have them,
        # so a reopened chat can re-render the numbered source rows. Plain URL
        # lists still work (older rows, chat replies).
        evidence    = json.dumps(_compact_articles(extra.get("evidence_articles")) or extra.get("evidence", [])),
    )
    db.add(msg)
    # Auto-title session from first user message
    # Use explicit title_override if provided (e.g. filename for uploads)
    if role == "user":
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session and session.title == "New Chat":
            title_override = extra.get("title_override")
            session.title = (title_override or content)[:60]
        if session:
            session.updated_at = datetime.utcnow()
    db.commit()
    return msg


# ── Helpers ──────────────────────────────────────────────────

def _get_session(session_id: int, user_id: int, db: Session) -> ChatSession:
    s = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return s


def _session_dict(s: ChatSession) -> dict:
    return {"id": s.id, "title": s.title, "created_at": s.created_at.isoformat(), "updated_at": s.updated_at.isoformat()}


def _compact_articles(articles, limit: int = 8):
    """Reduce evidence article dicts to small JSON-safe fields for storage."""
    keep = ("url", "title", "source", "publisher", "rating", "stance", "snippet", "published", "low_trust")
    out = []
    for a in (articles or [])[:limit]:
        if isinstance(a, dict) and a.get("url"):
            out.append({k: a[k] for k in keep if isinstance(a.get(k), (str, int, float, bool))})
    return out


def _msg_dict(m: ChatMessage) -> dict:
    evidence = []
    try:
        evidence = json.loads(m.evidence) if m.evidence else []
    except Exception:
        pass
    # Evidence is stored either as a list of URLs or a list of article dicts.
    # Always expose both shapes so the popup can render a fact-check card.
    evidence_articles = [e for e in evidence if isinstance(e, dict)]
    evidence = [e["url"] if isinstance(e, dict) else e for e in evidence if (e.get("url") if isinstance(e, dict) else e)]
    return {
        "id":          m.id,
        "role":        m.role,
        "content":     m.content,
        "is_claim":    m.is_claim,
        "verdict":     m.verdict,
        "confidence":  m.confidence,
        "ml_score":    m.ml_score,
        "ai_score":    m.ai_score,
        "explanation": m.explanation,
        "evidence":    evidence,
        "evidence_articles": evidence_articles,
        "created_at":  m.created_at.isoformat(),
    }
