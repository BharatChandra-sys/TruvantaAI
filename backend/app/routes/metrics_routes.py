# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
# Project: FactCheckAI � https://github.com/BharatChandra-sys/fake-news-extension
"""
Metrics Routes

Prometheus metrics endpoint and monitoring utilities.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import logging
import time

from database import get_db

logger = logging.getLogger(__name__)

from app.auth import get_current_user

router = APIRouter(tags=["metrics"], dependencies=[Depends(get_current_user)])

# Cached health metrics — recomputed at most once per 60 seconds
_health_cache: dict = {}
_health_cache_ts: float = 0.0
_HEALTH_TTL = 60.0


@router.get("/metrics")
def metrics_endpoint():
    """Prometheus metrics — DB update runs on background schedule, not here."""
    metrics_data = generate_latest()
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST,
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/health/metrics")
def health_metrics(db: Session = Depends(get_db)):
    """Health check with basic metrics (JSON). Cached for 60 seconds."""
    global _health_cache, _health_cache_ts

    now = time.time()
    if now - _health_cache_ts < _HEALTH_TTL and _health_cache:
        return _health_cache

    try:
        from app.models import ClaimRecord, UserFeedback, ABTest
        from datetime import datetime, timedelta
        from sqlalchemy import case, func

        since_24h = datetime.utcnow() - timedelta(hours=24)

        # Single aggregated query instead of 4 separate counts
        row = db.query(
            func.count(ClaimRecord.id).label("claims_24h"),
            func.sum(
                case((ClaimRecord.confidence >= 0.45, 1), else_=0)
            ).label("review_queue"),
        ).filter(ClaimRecord.created_at >= since_24h).one_or_none()

        reviews_24h  = db.query(func.count(UserFeedback.id)).filter(
            UserFeedback.created_at >= since_24h
        ).scalar() or 0
        active_tests = db.query(func.count(ABTest.id)).filter(
            ABTest.status == "active"
        ).scalar() or 0

        result = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": {
                "claims_processed_24h": row.claims_24h if row else 0,
                "reviews_submitted_24h": reviews_24h,
                "active_ab_tests": active_tests,
                "review_queue_size": row.review_queue if row else 0,
            },
        }
        _health_cache    = result
        _health_cache_ts = now
        return result

    except Exception as e:
        logger.error("Health metrics failed: %s", e)
        return {"status": "degraded", "error": str(e)}
