"""
Cross-Encoder Reranker

Takes a pool of ~30 hybrid-retrieved candidates and reranks them
using a cross-encoder model for precise relevance scoring.

Why cross-encoder over bi-encoder?
- Bi-encoder (used for retrieval): encodes query and document separately
  → fast but less accurate (no cross-attention between query and doc)
- Cross-encoder: encodes query+document together → slow but precise
  → ideal for reranking a small candidate pool (15-30 docs)

Model: ms-marco-MiniLM-L-6-v2 (22M parameters, trained on MS MARCO passage
ranking), from the first backend that loads, chosen with RERANKER_BACKEND:

  auto                   (default) fastembed, then sentence-transformers.
  fastembed              ONNX Runtime, no PyTorch: ~35 ms for 10 articles on
                         CPU, ~100 MB of memory beside local embeddings (~180 MB
                         alone). Set RERANKER_BACKEND=off on a 512 MB host.
  sentence-transformers  the same model on PyTorch.
  off                    no model; score() returns None.

score() is the shared entry point; it returns 0-1 relevance scores, or None
when no model is available, and callers then keep their own order. rerank()
falls back to the LLM-based scorer in cross_encoder.py.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)

_MODEL = "ms-marco-MiniLM-L-6-v2"
# The model reads at most 512 tokens per pair; longer text only costs tokenizing.
_MAX_CHARS = 1500

_lock = threading.Lock()
_backend: Optional[str] = None      # "fastembed" | "sentence-transformers" | "off", decided once
_predict: Optional[Callable[[str, list], np.ndarray]] = None


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _load_fastembed():
    from fastembed.rerank.cross_encoder import TextCrossEncoder
    model = TextCrossEncoder(f"Xenova/{_MODEL}")
    # fastembed returns raw logits.
    return lambda query, texts: _sigmoid(np.fromiter(model.rerank(query, texts), dtype=np.float32,
                                                     count=len(texts)))


def _load_sentence_transformers():
    from sentence_transformers import CrossEncoder
    model = CrossEncoder(f"cross-encoder/{_MODEL}")

    def predict(query, texts):
        out = np.asarray(model.predict([(query, t) for t in texts], show_progress_bar=False),
                         dtype=np.float32)
        # Recent versions apply a sigmoid to single-label models already; older ones return logits.
        return out if out.min() >= 0.0 and out.max() <= 1.0 else _sigmoid(out)
    return predict


_LOADERS = {"fastembed": _load_fastembed, "sentence-transformers": _load_sentence_transformers}


def _choose() -> str:
    global _backend, _predict
    if _backend is not None:
        return _backend
    with _lock:
        if _backend is not None:
            return _backend
        wanted = os.getenv("RERANKER_BACKEND", "auto").strip().lower()
        names = list(_LOADERS) if wanted == "auto" else [wanted] if wanted in _LOADERS else []
        _backend = "off"
        for name in names:
            try:
                _predict = _LOADERS[name]()
                _backend = name
                break
            except ImportError:
                logger.debug("Reranker: %s not installed", name)
            except Exception as e:
                logger.warning("Reranker: %s failed to load: %s", name, e)
        logger.info("Reranker: %s", f"{_backend} ({_MODEL})" if _backend != "off" else "off")
        return _backend


def available() -> bool:
    """True when a cross-encoder model is loaded."""
    return _choose() != "off"


def backend() -> str:
    return _choose()


def warm_up() -> None:
    """Load the model before the first check needs it."""
    threading.Thread(target=_choose, daemon=True, name="reranker-warmup").start()


def score(query: str, texts: list[str]) -> Optional[list[float]]:
    """
    Relevance of each text to the query, 0-1 (higher is more relevant), in the
    order given. None when no model is available or scoring fails.
    """
    if not texts:
        return []
    if not available():
        return None
    try:
        scores = _predict((query or "")[:_MAX_CHARS], [(t or "")[:_MAX_CHARS] for t in texts])
    except Exception as e:
        logger.warning("Reranker scoring failed (%s): %s", _backend, str(e)[:160])
        return None
    return [round(float(s), 4) for s in scores]


def rerank(
    claim:      str,
    candidates: list[dict],
    text_key:   str = "claim_text",
    top_k:      int = 5,
) -> list[dict]:
    """
    Rerank a candidate pool by relevance to the claim.

    Args:
        claim:      The claim being fact-checked.
        candidates: List of dicts, each with a text field (text_key).
        text_key:   Key in each dict that holds the text to score.
        top_k:      Number of top candidates to return after reranking.

    Returns:
        Top-k candidates sorted by cross-encoder score (descending),
        each with an added 'rerank_score' field.
    """
    if not candidates:
        return []

    if len(candidates) <= top_k:
        return candidates  # No need to rerank small pools

    scores = score(claim, [c.get(text_key, "") or c.get("title", "") for c in candidates])
    if scores is not None:
        for c, s in zip(candidates, scores):
            c["rerank_score"] = s
        # Stable sort: ties keep the retrieval order.
        ranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)
        logger.debug("Cross-encoder reranked %d → %d candidates", len(candidates), top_k)
        return ranked[:top_k]

    # Fallback: use LLM-based scorer from legacy cross_encoder.py
    try:
        from app.analysis.cross_encoder import rerank_articles
        return rerank_articles(claim, candidates, top_k=top_k)
    except Exception as e:
        logger.debug("LLM fallback reranker failed: %s", e)

    # Last resort: return top_k by RRF score
    sorted_by_rrf = sorted(
        candidates,
        key=lambda x: x.get("rrf_score", x.get("similarity", 0)),
        reverse=True
    )
    return sorted_by_rrf[:top_k]


def rerank_all(
    claim:     str,
    pool:      dict[str, list[dict]],
    total_k:   int = 8,
) -> list[dict]:
    """
    Rerank a balanced evidence pool (output of retrieve_balanced_evidence).

    Takes supporting + contradicting + neutral + authoritative + historical,
    deduplicates, reranks the combined pool, returns top total_k.

    Preserves stance diversity: always includes at least 1 supporting
    and 1 contradicting if they exist.
    """
    # Flatten and deduplicate by ID
    seen_ids: set = set()
    flat: list[dict] = []
    for group in pool.values():
        for item in group:
            item_id = item.get("id") or item.get("url", "")
            if item_id not in seen_ids:
                seen_ids.add(item_id)
                flat.append(item)

    if not flat:
        return []

    # Rerank the full pool
    text_key = "claim_text" if "claim_text" in flat[0] else "title"
    reranked = rerank(claim, flat, text_key=text_key, top_k=min(total_k + 5, len(flat)))

    # Ensure stance diversity: at least 1 supporting + 1 contradicting
    result: list[dict]  = []
    has_support     = False
    has_contradict  = False

    for item in reranked:
        stance = item.get("stance", "neutral")
        if not has_support and stance == "support":
            result.insert(0, item)
            has_support = True
        elif not has_contradict and stance == "contradict":
            result.append(item)
            has_contradict = True
        else:
            result.append(item)

        if len(result) >= total_k:
            break

    return result[:total_k]
