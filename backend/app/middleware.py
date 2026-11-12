# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
# Project: FactCheckAI � https://github.com/BharatChandra-sys/fake-news-extension
"""
Security + observability middleware.

- Rate limiting (per-IP, per-route, in-memory sliding window)
- Request body size guard
- Security headers (HSTS, X-Frame-Options, etc.)
- Request ID injection (X-Request-ID header)
- Structured request logging (method, path, status, duration, request_id)
"""
import hashlib
import time
import uuid
import logging
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# ── Rate limit config per route prefix ───────────────────────
_LIMITS = {
    "/auth/login":           (10,  60),
    "/auth/signup":          (5,   60),
    "/auth/forgot-password": (5,  300),
    "/auth/reset-password":  (5,   60),
    "/auth/google":          (10,  60),
    "/check/stream":         (15,  60),   # each check can cost two model calls
    "/message":              (20,  60),   # Lowered from 30 to protect AI limits
    "/feedback":             (20,  60),
    "/stats":                (30,  60),
    "/credibility":          (20,  60),
    "/history":              (60,  60),
}
_DEFAULT_LIMIT = (60, 60)

_store: dict = defaultdict(list)
last_activity = 0.0   # time of the last real request (health checks and keep-alive pings excluded)
MAX_BODY_BYTES = 2 * 1024 * 1024  # 2 MB — allows compressed image base64
_last_store_cleanup = 0.0
_STORE_CLEANUP_INTERVAL = 300  # prune every 5 minutes

# Security headers applied to every response
_SECURITY_HEADERS = {
    "X-Content-Type-Options":    "nosniff",
    "X-Frame-Options":           "DENY",
    "X-XSS-Protection":          "1; mode=block",
    "Referrer-Policy":           "strict-origin-when-cross-origin",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Permissions-Policy":        "geolocation=(), microphone=(), camera=()",
    "Content-Security-Policy":   (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none';"
    ),
}


def _get_limit(path: str):
    """The limit for a path and the bucket it counts against.

    The bucket is the matching route group, not the full path, so
    /history/sessions/1 and /history/sessions/2 share one allowance.
    """
    for prefix, limit in _LIMITS.items():
        if path.startswith(prefix):
            return limit, prefix
    return _DEFAULT_LIMIT, "/" + path.strip("/").split("/", 1)[0]


def _caller(request: Request, path: str) -> str:
    """Who to count a request against: the signed-in user's token when there is
    one, otherwise the IP. X-Forwarded-For can be set by the client, so a token
    is the stronger key. Sign-in routes always count by IP: a made-up token must
    not buy extra login attempts."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer ") and not path.startswith("/auth"):
        return "t:" + hashlib.sha256(auth.encode()).hexdigest()[:16]
    return _client_ip(request)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    return forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
        start = time.perf_counter()

        # ── Skip health checks ────────────────────────────────
        if path.startswith("/health"):
            response = await call_next(request)
            return response
        global last_activity
        last_activity = time.time()

        # ── Request body size guard ───────────────────────────
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large (max 2 MB)"},
            )

        # ── Rate limiting ─────────────────────────────────────
        (max_req, window), bucket = _get_limit(path)
        ip  = _client_ip(request)
        key = f"{_caller(request, path)}:{bucket}"
        now = time.time()

        # Periodic cleanup to prevent unbounded memory growth
        global _last_store_cleanup
        if now - _last_store_cleanup > _STORE_CLEANUP_INTERVAL:
            stale = [k for k, ts in _store.items() if not ts or ts[-1] < now - 3600]
            for k in stale:
                del _store[k]
            _last_store_cleanup = now

        _store[key] = [t for t in _store[key] if t > now - window]

        if len(_store[key]) >= max_req:
            logger.warning("rate_limit ip=%s path=%s request_id=%s", ip, path, request_id)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down."},
                headers={"Retry-After": str(window), "X-Request-ID": request_id},
            )
        _store[key].append(now)

        # ── Process request ───────────────────────────────────
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 1)

        # ── Structured access log ─────────────────────────────
        logger.info(
            "request method=%s path=%s status=%s duration_ms=%s ip=%s request_id=%s",
            request.method, path, response.status_code, duration_ms, ip, request_id,
        )

        # ── Security headers ──────────────────────────────────
        for header, value in _SECURITY_HEADERS.items():
            response.headers[header] = value
        response.headers["X-Request-ID"] = request_id

        return response
