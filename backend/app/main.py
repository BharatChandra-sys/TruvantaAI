# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
# Project: FactCheckAI � https://github.com/BharatChandra-sys/fake-news-extension
import os
import sys
import asyncio
import logging
import json
import math
import warnings
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

# Suppress scikit-learn version warnings (models trained on 1.6.1)
warnings.filterwarnings('ignore', category=UserWarning, module='sklearn')

# ── Custom JSON encoder — sanitize nan/inf from numpy/sklearn ─
class _SafeJSONEncoder(json.JSONEncoder):
    """Replace nan/inf float values with None so JSON serialization never crashes."""
    def iterencode(self, o, _one_shot=False):
        return super().iterencode(self._sanitize(o), _one_shot)

    def _sanitize(self, obj):
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        if isinstance(obj, dict):
            return {k: self._sanitize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._sanitize(v) for v in obj]
        return obj

# Monkey-patch FastAPI's default JSON encoder
import fastapi.responses as _fr
_orig_render = _fr.JSONResponse.render

def _safe_render(self, content):
    try:
        return _orig_render(self, content)
    except (ValueError, OverflowError):
        # Fallback: sanitize all floats then re-encode
        import numpy as np

        def _fix(obj):
            if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
                return None
            if hasattr(obj, 'item'):  # numpy scalar
                v = obj.item()
                return None if (isinstance(v, float) and (math.isnan(v) or math.isinf(v))) else v
            if isinstance(obj, dict):
                return {k: _fix(v) for k, v in obj.items()}
            if isinstance(obj, (list, tuple)):
                return [_fix(v) for v in obj]
            return obj

        return json.dumps(_fix(content), allow_nan=False).encode("utf-8")

_fr.JSONResponse.render = _safe_render

from database import engine, Base
import app.models  # register models
from app.api import router
from app.routes.auth_routes import router as auth_router
from app.routes.history_routes import router as history_router
from app.routes.stats_routes import router as stats_router
from app.routes.explain_routes import router as explain_router
from app.routes.review_routes import router as review_router
from app.routes.ab_routes import router as ab_router
from app.routes.metrics_routes import router as metrics_router
from app.routes.websocket_routes import router as websocket_router
from app.routes.cache_routes import router as cache_router
from app.routes.quota_routes import router as quota_router
from app.routes.analytics_routes import router as analytics_router
from app.routes.audio_routes import router as audio_router
from app.routes.viral_routes import router as viral_router
from app.routes.upload_routes import router as upload_router
from app.health import router as health_router
from app.middleware import SecurityMiddleware

# ── Structured JSON logging ───────────────────────────────────
class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log = {
            "ts":      self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level":   record.levelname,
            "logger":  record.name,
            "msg":     record.getMessage(),
        }
        if record.exc_info:
            log["exc"] = self.formatException(record.exc_info)
        return json.dumps(log)

_handler = logging.StreamHandler()
_handler.setFormatter(_JsonFormatter())
logging.root.handlers = [_handler]
logging.root.setLevel(logging.INFO)
logger = logging.getLogger(__name__)


class _SuppressHealthLogs(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "/health" not in record.getMessage()

logging.getLogger("uvicorn.access").addFilter(_SuppressHealthLogs())


@asynccontextmanager
async def lifespan(app: FastAPI):

    # Load the embedding model and open a memory read connection in the background,
    # so the first check doesn't pay for either.
    try:
        from app.retrieval.memory import warm_up
        warm_up()
    except Exception as e:
        logger.warning("Memory warm-up skipped: %s", e)

    # The language detector loads its profiles on first use (~300 ms); pay that now.
    def _warm_language():
        try:
            from app.analysis.multilingual import detect_language
            detect_language("Warm up the language detector before the first check.")
        except Exception as e:
            logger.debug("Language detector warm-up skipped: %s", e)
    import threading as _threading
    _threading.Thread(target=_warm_language, daemon=True, name="lang-warmup").start()

    # ── Step 1: Verify database connectivity ─────────────────
    # Retry up to 5 times with backoff — Neon wakes from auto-suspend in ~1s
    import time as _time
    from sqlalchemy import text as _text

    _db_ok = False
    for attempt in range(1, 4):  # Reduced from 5 to 3 attempts
        try:
            with engine.connect() as _conn:
                _conn.execute(_text("SELECT 1"))
            _db_ok = True
            logger.info("Database connection verified (attempt %d)", attempt)
            break
        except Exception as e:
            wait = attempt  # Reduced from attempt*2: 1s, 2s, 3s instead of 2s, 4s, 6s, 8s, 10s
            logger.warning("DB connection attempt %d failed: %s — retrying in %ds", attempt, e, wait)
            _time.sleep(wait)

    if not _db_ok:
        logger.error("Database unreachable after 3 attempts — check DATABASE_URL and Neon project status")
        # Don't crash — app can still serve health checks and static responses

    # ── Step 2: Create all tables from SQLAlchemy models ─────
    # create_all is idempotent — skips existing tables, creates missing ones
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Table check complete (create_all — no-op for existing tables)")
    except Exception as e:
        logger.error("create_all failed: %s", e)

    # ── Step 3: Run Alembic migrations ───────────────────────
    # Runs on every deploy — no-op if already at head
    # Adds new columns/indexes without dropping existing data
    # Skip if DATABASE_URL not set (local dev mode)
    if os.getenv("DATABASE_URL"):
        try:
            import subprocess, sys
            alembic_ini = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "alembic.ini")
            if os.path.exists(alembic_ini):
                result = subprocess.run(
                    [sys.executable, "-m", "alembic", "-c", alembic_ini, "upgrade", "head"],
                    capture_output=True, text=True, timeout=60,  # Reduced from 120s to 60s
                    env={**os.environ, "PYTHONUNBUFFERED": "1"},
                )
                if result.returncode == 0:
                    out = result.stdout.strip() or "already at head"
                    logger.info("Alembic migrations: %s", out)
                else:
                    logger.warning("Alembic migration warning: %s", result.stderr.strip())
            else:
                logger.debug("alembic.ini not found — skipping Alembic (SQLite dev mode)")
        except subprocess.TimeoutExpired:
            logger.error("Alembic migration timed out after 60s — skipping")
        except Exception as e:
            logger.warning("Alembic migration failed: %s — tables already created via create_all", e)
    else:
        logger.info("DATABASE_URL not set — skipping Alembic (local dev mode)")

    # ── Step 4: Verify critical tables exist ─────────────────
    # Belt-and-suspenders check: log any model table that's missing from DB
    from sqlalchemy import inspect as _inspect
    try:
        inspector   = _inspect(engine)
        db_tables   = set(inspector.get_table_names())
        model_tables = set(Base.metadata.tables.keys())
        missing = model_tables - db_tables
        if missing:
            logger.warning("Tables still missing after migration: %s — attempting create_all again", missing)
            Base.metadata.create_all(bind=engine)
        else:
            logger.info("All %d model tables present in database", len(model_tables))
    except Exception as e:
        logger.warning("Table verification failed: %s", e)

    # ── Load TF-IDF model only (fast, ~50ms) ──────────────────
    # RoBERTa is NOT preloaded — it's 500MB and would time out Render's
    # health check. It loads lazily on first request instead.
    try:
        from app.analysis.ml import _load_tfidf
        _load_tfidf()
        logger.info("TF-IDF model preloaded")
    except Exception as e:
        logger.warning("TF-IDF preload failed: %s", e)

    # ── Warm up AI model discovery cache ──────────────────────
    # Pre-fetches available models from Groq, Cerebras, Gemini.
    # Runs in background thread so it doesn't block startup.
    try:
        import threading
        def _warmup():
            try:
                from app.analysis.ai_config import warmup_model_cache
                warmup_model_cache()
            except Exception as e:
                logger.warning("Model cache warmup failed: %s", e)
        threading.Thread(target=_warmup, daemon=True, name="model-cache-warmup").start()
        logger.info("Model cache warmup started in background")
    except Exception as e:
        logger.warning("Could not start model cache warmup: %s", e)

    # ── Train TF-IDF if no model file exists ──────────────────
    if os.getenv("SKIP_TRAIN_ON_STARTUP", "false").lower() != "true":
        model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "model.joblib")
        if not os.path.exists(model_path):
            try:
                train_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "training", "train.py")
                proc = await asyncio.create_subprocess_exec(
                    sys.executable, train_script,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
                if proc.returncode == 0:
                    logger.info("ML model trained on startup")
                else:
                    logger.warning("ML training failed: %s", stderr.decode()[:200] if stderr else "unknown")
            except asyncio.TimeoutError:
                logger.warning("ML training timed out — will use default 0.5 until model is built")
            except Exception as e:
                logger.warning("ML training failed on startup: %s", e)

    # ── Pre-warm sentence-transformers (avoids 30s cold-start on first claim) ─
    # Only runs if sentence-transformers is installed (not on Render free tier)
    try:
        from app.analysis.semantic_clustering import _get_sentence_transformer
        _get_sentence_transformer()
        logger.info("Sentence-transformers model pre-warmed")
    except (ImportError, Exception) as e:
        logger.debug("Sentence-transformers pre-warm skipped: %s", e)

    # ── Start background data collection scheduler ────────────
    # Collects fresh labeled training data every 24h from web search + fact-checkers
    # Non-blocking — runs in a daemon thread
    try:
        import threading, time as _time
        from database import SessionLocal

        def _collection_scheduler():
            """
            Two jobs in one thread:
            1. Every 14 minutes: self-ping /health AND ping ML Server 2 (HF Spaces)
               to prevent both Render and HF Spaces from sleeping.
               NOTE: Render blocks self-pings from inside the same service.
               This ping works for HF Spaces and any external service.
               For Render itself, configure UptimeRobot (free) to ping /health every 5 min.
            2. Every hour: check if training data collection should be triggered.
            """
            _time.sleep(5)  # brief pause after startup (reduced from 60s to 5s)
            last_collection_check = 0.0

            while True:
                now = _time.time()

                # ── Keep-alive pings (every 14 min) ───────────────
                try:
                    import requests as _req
                    
                    # Ping ML Server 2 (HF Spaces) to prevent sleeping
                    ml2 = os.getenv("ML_SERVER_2_URL")
                    if ml2:
                        try:
                            # Use HEAD request to minimize bandwidth (HF Spaces stays awake ~15 min after any activity)
                            response = _req.head(ml2, timeout=10, allow_redirects=True)
                            if response.status_code in (200, 301, 302, 405):  # 405 = Method Not Allowed is OK
                                logger.debug("✓ ML Server 2 (HF Space) keep-alive successful")
                            else:
                                logger.warning("ML Server 2 keep-alive status %d", response.status_code)
                        except _req.exceptions.Timeout:
                            logger.debug("ML Server 2 keep-alive timeout (may be waking from sleep)")
                        except Exception as e:
                            logger.warning("ML Server 2 keep-alive failed: %s", e)
                    
                    # Ping ML Server 1 healthcheck (if configured)
                    ml1 = os.getenv("ML_SERVER_1_URL")
                    if ml1:
                        try:
                            _req.head(f"{ml1}/health", timeout=5)
                            logger.debug("✓ ML Server 1 keep-alive successful")
                        except Exception as e:
                            logger.debug("ML Server 1 keep-alive failed: %s", e)
                            
                except Exception as e:
                    logger.debug("Keep-alive scheduler error: %s", e)

                # ── Data collection (every hour) ──────────────────
                if now - last_collection_check >= 3600:
                    try:
                        from app.analysis.continuous_learning import maybe_collect_data
                        result = maybe_collect_data(SessionLocal)
                        if result.get("triggered"):
                            logger.info("Background data collection triggered: %s", result.get("reason"))
                    except Exception as e:
                        logger.debug("Collection scheduler error: %s", e)

                    # Update Prometheus metrics on the same 1h cycle
                    try:
                        from app.monitoring import update_review_queue_metrics, update_model_accuracy_metrics
                        _db = SessionLocal()
                        try:
                            update_review_queue_metrics(_db)
                            update_model_accuracy_metrics(_db)
                        finally:
                            _db.close()
                    except Exception as e:
                        logger.debug("Prometheus metric update error: %s", e)

                    last_collection_check = now

                _time.sleep(840)  # 14 minutes — just under Render's 15-min sleep threshold

        _sched_thread = threading.Thread(
            target=_collection_scheduler,
            daemon=True,
            name="background-scheduler",
        )
        _sched_thread.start()
        logger.info("Background scheduler started (keep-alive every 14min, data collection every 1h)")
    except Exception as e:
        logger.warning("Background scheduler failed to start: %s", e)

    yield

    # ── Graceful shutdown ─────────────────────────────────────
    try:
        from app.analysis.ai import _POOL
        _POOL.shutdown(wait=False, cancel_futures=True)
        logger.info("AI thread pool shut down")
    except Exception as e:
        logger.debug("AI pool shutdown: %s", e)


app = FastAPI(
    title="FactCheckAI",
    version="2.6.1",
    lifespan=lifespan,
    description="FactCheckAI — AI-powered fact-checking API with ML models, evidence search, and real-time verification",
    # Disable docs in production — set ENABLE_DOCS=true to re-enable for debugging
    docs_url="/docs" if os.getenv("ENABLE_DOCS", "false").lower() == "true" else None,
    redoc_url="/redoc" if os.getenv("ENABLE_DOCS", "false").lower() == "true" else None,
    openapi_url="/openapi.json" if os.getenv("ENABLE_DOCS", "false").lower() == "true" else None,
)

# ── CORS — Allow browser extensions + web frontends ─────────────
_RAW_ALLOWED = os.getenv("ALLOWED_ORIGINS", "")
_ENV_ORIGINS = [o.strip() for o in _RAW_ALLOWED.split(",") if o.strip()]

# Default: localhost for local development
# Browser extensions (chrome-extension://, extension://) are always allowed via regex below
# Add your web app URLs to ALLOWED_ORIGINS env var if you deploy a web frontend
ALLOWED_ORIGINS = _ENV_ORIGINS or ["http://localhost:3000", "http://127.0.0.1:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"(chrome-extension://.*|extension://.*)",  # Chrome + Edge extensions
    allow_methods=["GET", "POST", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Client", "X-Client-Version", "X-Request-ID"],
    allow_credentials=True,
    max_age=600,
)

# ── Security middleware (rate limiting + headers) ─────────────
app.add_middleware(SecurityMiddleware)

# ── Rate limit headers middleware ─────────────────────────────
from app.rate_limit import add_rate_limit_headers
app.middleware("http")(add_rate_limit_headers)

# ── Routers ───────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(history_router)
app.include_router(stats_router)
app.include_router(explain_router)
app.include_router(review_router)
app.include_router(ab_router)
app.include_router(metrics_router)
app.include_router(websocket_router)
app.include_router(cache_router)
from app.routes.stream_routes import router as stream_router
app.include_router(stream_router)   # POST /check/stream (real-time check)
app.include_router(quota_router)
app.include_router(analytics_router)
app.include_router(audio_router)
app.include_router(viral_router)
app.include_router(upload_router)
app.include_router(health_router)
app.include_router(router)
