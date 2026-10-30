"""
Embedding Service

384-dim, L2-normalized sentence embeddings for claim memory, from one of two
backends, chosen with EMBEDDINGS_BACKEND:

  gemini  (default when GEMINI_API_KEY is set) gemini-embedding-001 through
          Google's free API, truncated to 384 dimensions. Uses no server memory,
          which matters on a 512 MB host where the live app already needs
          ~320 MB. About 0.1-0.5 s per claim, so lookups run beside the search.
  local   all-MiniLM-L6-v2 on ONNX Runtime through fastembed (optional
          dependency): ~2 ms per claim, but ~180 MB of memory.
  off     no embeddings; claim memory switches off.

Vectors from different models live in different spaces, so every stored
vector is tagged with model_id() and only compared with vectors of the same
model. Similarity scales differ too: thresholds() gives each model's own.

There is deliberately no hashing fallback: a pseudo-embedding would corrupt
every similarity search. Without a working backend, embed() returns None and
callers skip the vector step.

Usage:
    from app.retrieval.embeddings import embed, embed_batch
    vec = embed("5G towers spread COVID")   # list[float] len=384, or None
"""
from __future__ import annotations

import hashlib
import logging
import os
import threading
from collections import OrderedDict
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384
_MAX_CHARS = 512

_GEMINI_MODEL = "gemini-embedding-001"
_GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{_GEMINI_MODEL}:batchEmbedContents"
_GEMINI_TIMEOUT_S = 3.0
_LOCAL_MODEL = "all-MiniLM-L6-v2"

# Measured on the evaluation claims (October 2026). "match" is the similarity a
# reworded claim reaches (word order, negations and numbers are checked
# separately); "related" sits above what unrelated claims reach.
#   gemini: unrelated p99 0.82, same topic/different claim 0.90-0.95, rewordings 0.975-0.99
#   local:  unrelated < 0.75, same topic/different claim 0.81-0.84, rewordings 0.89-0.97
_THRESHOLDS = {
    "gemini": {"match": 0.97, "related": 0.85},
    "local": {"match": 0.92, "related": 0.75},
}

_lock = threading.Lock()
_backend: Optional[str] = None      # "gemini" | "local" | "off", decided once
_local_encode = None
_session = None

# Claims repeat within minutes (warm-up, check, follow-up): a small in-process
# LRU saves recomputation, and for the remote backend a network call.
_LRU_SIZE = 2048
_lru: "OrderedDict[str, list[float]]" = OrderedDict()
_lru_lock = threading.Lock()


# ── Backend choice ────────────────────────────────────────────

def _choose() -> str:
    global _backend, _local_encode, _session
    if _backend is not None:
        return _backend
    with _lock:
        if _backend is not None:
            return _backend
        wanted = os.getenv("EMBEDDINGS_BACKEND", "").strip().lower()
        if not wanted:
            wanted = "gemini" if os.getenv("GEMINI_API_KEY") else "local"
        if wanted == "gemini" and os.getenv("GEMINI_API_KEY"):
            import requests
            _session = requests.Session()
            _backend = "gemini"
        elif wanted == "local":
            try:
                from fastembed import TextEmbedding
                model = TextEmbedding(f"sentence-transformers/{_LOCAL_MODEL}")
                _local_encode = lambda texts: np.asarray(list(model.embed(texts)), dtype=np.float32)
                _backend = "local"
            except Exception as e:
                logger.warning("Local embeddings unavailable (%s); claim memory is off", e)
                _backend = "off"
        else:
            _backend = "off"
        logger.info("Embeddings: %s", model_id() or "off")
        return _backend


def available() -> bool:
    """True when real embeddings can be produced."""
    return _choose() != "off"


def backend() -> Optional[str]:
    return _choose()


def model_id() -> Optional[str]:
    """Which vector space a stored vector belongs to; vectors only compare within one."""
    return {"gemini": f"{_GEMINI_MODEL}@{EMBEDDING_DIM}", "local": _LOCAL_MODEL}.get(_choose())


def thresholds() -> dict:
    return _THRESHOLDS.get(_choose(), _THRESHOLDS["local"])


def warm_up() -> None:
    """Pick the backend (and load a local model) before the first check needs it."""
    threading.Thread(target=_choose, daemon=True, name="embed-warmup").start()


# ── Encoders ──────────────────────────────────────────────────

def _gemini_encode(texts: list[str]) -> np.ndarray:
    body = {"requests": [{
        "model": f"models/{_GEMINI_MODEL}",
        "content": {"parts": [{"text": t}]},
        "outputDimensionality": EMBEDDING_DIM,
        "taskType": "SEMANTIC_SIMILARITY",
    } for t in texts]}
    r = _session.post(_GEMINI_URL, params={"key": os.getenv("GEMINI_API_KEY")}, json=body,
                      timeout=_GEMINI_TIMEOUT_S)
    r.raise_for_status()
    vecs = np.asarray([e["values"] for e in r.json()["embeddings"]], dtype=np.float32)
    # Truncated Gemini vectors are not unit length; normalize so cosine = dot.
    return vecs / np.linalg.norm(vecs, axis=1, keepdims=True)


def _encode(texts: list[str]) -> np.ndarray:
    b = _choose()
    if b == "gemini":
        return _gemini_encode(texts)
    if b == "local":
        return _local_encode(texts)
    raise RuntimeError("no embedding backend")


# ── Cache helpers ─────────────────────────────────────────────

def _key(text: str) -> str:
    return hashlib.sha256(text.lower().encode()).hexdigest()[:20]


def _lru_get(text: str) -> Optional[list[float]]:
    k = _key(text)
    with _lru_lock:
        v = _lru.get(k)
        if v is not None:
            _lru.move_to_end(k)
        return v


def _lru_set(text: str, vec: list[float]) -> None:
    k = _key(text)
    with _lru_lock:
        _lru[k] = vec
        _lru.move_to_end(k)
        while len(_lru) > _LRU_SIZE:
            _lru.popitem(last=False)


def _clean(text: str) -> str:
    return " ".join((text or "").split())[:_MAX_CHARS]


# ── Public API ────────────────────────────────────────────────

def embed(text: str) -> Optional[list[float]]:
    """Embed one text. Returns a normalized 384-dim list, or None without a backend."""
    return embed_batch([text])[0]


def embed_batch(texts: list[str]) -> list[Optional[list[float]]]:
    """Embed many texts in one call; cached texts are not recomputed."""
    cleaned = [_clean(t) for t in texts]
    out: list[Optional[list[float]]] = [None] * len(cleaned)
    todo = []
    for i, t in enumerate(cleaned):
        if not t:
            continue
        hit = _lru_get(t)
        if hit is not None:
            out[i] = hit
        else:
            todo.append(i)
    if todo and available():
        try:
            vecs = _encode([cleaned[i] for i in todo])
            for i, v in zip(todo, vecs):
                out[i] = v.tolist()
                _lru_set(cleaned[i], out[i])
        except Exception as e:
            logger.warning("Embedding failed (%s): %s", _backend, str(e)[:160])
    return out


def to_pgvector(vec: list[float]) -> str:
    """pgvector's text format. Six decimals keep full float32 precision for cosine."""
    return "[" + ",".join(f"{v:.6f}" for v in vec) + "]"


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two embedding vectors."""
    va, vb = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    return float(va @ vb / denom) if denom else 0.0
