"""
Embedding Service

384-dim, L2-normalized sentence embeddings from all-MiniLM-L6-v2.

The model runs on ONNX Runtime through fastembed: about 2 ms per claim and
~180 MB of memory, against ~590 MB and a 20 s load for the PyTorch version.
Both produce the same vectors (cosine 1.0), so stored rows stay valid either
way; sentence-transformers is used only when fastembed is missing.

There is deliberately no hashing fallback. A pseudo-embedding lives in a
different vector space, and mixing it into pgvector would silently corrupt
every similarity search. Without a real model, embed() returns None and
callers skip the vector step.

Usage:
    from app.retrieval.embeddings import embed, embed_batch
    vec = embed("5G towers spread COVID")   # list[float] len=384, or None
"""
from __future__ import annotations

import hashlib
import logging
import threading
from collections import OrderedDict
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

EMBEDDING_DIM = 384
_MODEL_NAME   = "all-MiniLM-L6-v2"
_MAX_CHARS    = 512        # the model reads 256 tokens; longer text is wasted work

_encode = None             # callable(list[str]) -> np.ndarray, normalized rows
_backend: Optional[str] = None
_load_lock = threading.Lock()
_load_failed = False

# Claims repeat within minutes (warm-up, check, follow-up), so a small
# in-process LRU saves recomputation without a network round trip to Redis.
_LRU_SIZE = 2048
_lru: "OrderedDict[str, list[float]]" = OrderedDict()
_lru_lock = threading.Lock()


# ── Model loading ─────────────────────────────────────────────

def _load() -> bool:
    """Load the fastest available backend once. Returns True when one is ready."""
    global _encode, _backend, _load_failed
    if _encode is not None:
        return True
    if _load_failed:
        return False
    with _load_lock:
        if _encode is not None:
            return True
        try:
            from fastembed import TextEmbedding
            model = TextEmbedding(f"sentence-transformers/{_MODEL_NAME}")
            _encode = lambda texts: np.asarray(list(model.embed(texts)), dtype=np.float32)
            _backend = "fastembed-onnx"
        except Exception as e:
            logger.info("fastembed unavailable (%s); trying sentence-transformers", e)
            try:
                from sentence_transformers import SentenceTransformer
                model = SentenceTransformer(_MODEL_NAME)
                _encode = lambda texts: model.encode(texts, normalize_embeddings=True,
                                                     convert_to_numpy=True, show_progress_bar=False)
                _backend = "sentence-transformers"
            except Exception as e2:
                logger.warning("No embedding model available, vector memory is off: %s", e2)
                _load_failed = True
                return False
        logger.info("Embedding model loaded: %s via %s", _MODEL_NAME, _backend)
        return True


def available() -> bool:
    """True when real embeddings can be produced."""
    return _load()


def backend() -> Optional[str]:
    return _backend


def warm_up() -> None:
    """Load the model in the background so the first check doesn't pay for it."""
    threading.Thread(target=_load, daemon=True, name="embed-warmup").start()


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
    """Embed one text. Returns a normalized 384-dim list, or None without a model."""
    text = _clean(text)
    if not text:
        return None
    cached = _lru_get(text)
    if cached is not None:
        return cached
    if not _load():
        return None
    try:
        vec = _encode([text])[0].tolist()
    except Exception as e:
        logger.warning("Embedding failed: %s", e)
        return None
    _lru_set(text, vec)
    return vec


def embed_batch(texts: list[str]) -> list[Optional[list[float]]]:
    """Embed many texts in one model call; cached texts are not recomputed."""
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
    if todo and _load():
        try:
            vecs = _encode([cleaned[i] for i in todo])
            for i, v in zip(todo, vecs):
                out[i] = v.tolist()
                _lru_set(cleaned[i], out[i])
        except Exception as e:
            logger.warning("Batch embedding failed: %s", e)
    return out


def to_pgvector(vec: list[float]) -> str:
    """pgvector's text format. Six decimals keep full float32 precision for cosine."""
    return "[" + ",".join(f"{v:.6f}" for v in vec) + "]"


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two embedding vectors."""
    va, vb = np.asarray(a, dtype=np.float32), np.asarray(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    return float(va @ vb / denom) if denom else 0.0
