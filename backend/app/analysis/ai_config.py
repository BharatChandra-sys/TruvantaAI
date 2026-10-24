"""
Central AI Provider Configuration
Discovers each provider's current models at runtime and caches them.
No model IDs are hard-coded: ordering comes from model_registry, which
ranks by observed health first and by capability (from the name) second.
"""
import os
import time
import logging
import threading
import requests
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

from app.analysis.model_registry import capability_rank, registry

logger = logging.getLogger(__name__)

# API URLs
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_URL_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
MINIMAX_URL = "https://api.minimax.io/v1/chat/completions"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model families that can't answer a chat prompt (audio, embeddings, safety
# classifiers, image generation). Matched as substrings of the model ID.
_NON_CHAT = ("whisper", "embed", "guard", "tts", "text-to-speech", "orpheus",
             "playai", "imagen", "image-generation", "aqa", "transcribe", "moderation")


@lru_cache(maxsize=10)
def get_api_keys() -> dict:
    """Get API keys from environment (cached)."""
    return {
        "cerebras": os.getenv("CEREBRAS_API_KEY"),
        "groq": os.getenv("GROQ_API_KEY"),
        "gemini": os.getenv("GEMINI_API_KEY"),
        "minimax": os.getenv("MINIMAX_API_KEY"),
        "openrouter": os.getenv("OPENROUTER_API_KEY"),
        "gemini_proxy": os.getenv("GEMINI_WEB2API_URL", "https://factcheckai-gemini-proxy.onrender.com"),
    }


# provider → (expires_at, models)
_MODEL_CACHE: Dict[str, Tuple[float, List[str]]] = {}
# provider → last non-empty discovery result, used when discovery itself fails
_LAST_GOOD: Dict[str, List[str]] = {}
_CACHE_TTL_SECONDS = 3600         # 1 hour for a successful discovery
_FAILED_DISCOVERY_TTL_SECONDS = 120  # don't re-ask an unreachable provider on every request
_CACHE_LOCK = threading.Lock()


def _cached(provider: str) -> Optional[List[str]]:
    with _CACHE_LOCK:
        entry = _MODEL_CACHE.get(provider)
        if entry and time.time() < entry[0]:
            return entry[1]
    return None


def _store(provider: str, models: List[str]) -> List[str]:
    with _CACHE_LOCK:
        _MODEL_CACHE[provider] = (time.time() + _CACHE_TTL_SECONDS, models)
        if models:
            _LAST_GOOD[provider] = models
    return models


def _fallback(provider: str) -> List[str]:
    """
    Discovery failed: reuse the last list that worked (the registry skips
    dead models) and don't ask again for a couple of minutes.
    """
    with _CACHE_LOCK:
        models = list(_LAST_GOOD.get(provider, []))
        _MODEL_CACHE[provider] = (time.time() + _FAILED_DISCOVERY_TTL_SECONDS, models)
        return models


def invalidate_discovery(provider: str) -> None:
    """Forget the cached model list so the next call asks the provider again."""
    key = "gemini_proxy" if provider == "gemini_proxy" else provider
    with _CACHE_LOCK:
        _MODEL_CACHE.pop(key, None)
    logger.info("Model list for %s will be re-discovered on next use", key)


# A model that disappears is a sign the provider's lineup changed.
registry.on_permanent_failure(invalidate_discovery)


def _chat_models(models: List[str]) -> List[str]:
    """Drop non-chat models and order the rest by capability."""
    usable = [m for m in models if not any(x in m.lower() for x in _NON_CHAT)]
    return sorted(dict.fromkeys(usable), key=capability_rank, reverse=True)


def _discover(provider: str, fetch) -> List[str]:
    """Current chat models for a provider: best first, models on hold left out."""
    models = _cached(provider)
    if models is None:
        try:
            models = _store(provider, _chat_models(fetch()))
            logger.info("Discovered %d %s models", len(models), provider)
        except Exception as e:
            logger.warning("%s model discovery failed: %s", provider, e)
            models = _fallback(provider)
    return registry.ranked(provider, models)


def _get_json(url: str, **kwargs) -> dict:
    r = requests.get(url, timeout=10, **kwargs)
    r.raise_for_status()
    return r.json()


def discover_groq_models(api_key: str) -> List[str]:
    """Discover available Groq chat models."""
    return _discover("groq", lambda: [
        m["id"] for m in _get_json(
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        ).get("data", [])
        if m.get("active", True)
    ])


def discover_cerebras_models(api_key: str) -> List[str]:
    """Discover available Cerebras chat models."""
    return _discover("cerebras", lambda: [
        m["id"] for m in _get_json(
            "https://api.cerebras.ai/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        ).get("data", [])
    ])


def discover_gemini_models(api_key: str) -> List[str]:
    """Discover Gemini/Gemma models that support generateContent."""
    return _discover("gemini", lambda: [
        m["name"].replace("models/", "")
        for m in _get_json(GEMINI_URL_BASE, params={"key": api_key}).get("models", [])
        if "generateContent" in m.get("supportedGenerationMethods", [])
    ])


def discover_gemini_proxy_models(proxy_url: str) -> List[str]:
    """Discover models served by the Gemini web2api proxy."""
    return _discover("gemini_proxy", lambda: [
        m["id"] for m in _get_json(f"{proxy_url}/v1/models").get("data", [])
    ])


def discover_openrouter_models(api_key: str) -> List[str]:
    """Discover OpenRouter models that are free to call."""
    def fetch():
        data = _get_json(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        ).get("data", [])
        return [
            m["id"] for m in data
            if str(m.get("pricing", {}).get("prompt", "1")) in ("0", "0.0")
            and str(m.get("pricing", {}).get("completion", "0")) in ("0", "0.0")
        ]
    return _discover("openrouter", fetch)


_DISCOVERERS = {
    "groq": ("groq", discover_groq_models),
    "cerebras": ("cerebras", discover_cerebras_models),
    "gemini": ("gemini", discover_gemini_models),
    "gemini_proxy": ("gemini_proxy", discover_gemini_proxy_models),
    "openrouter": ("openrouter", discover_openrouter_models),
}


def get_all_working_models(provider: str) -> List[str]:
    """Usable models for a provider, best first, skipping ones on hold."""
    entry = _DISCOVERERS.get(provider)
    if not entry:
        return []
    key_name, discover = entry
    key = get_api_keys().get(key_name)
    if not key:
        return []
    return registry.ranked(provider, discover(key))


def get_first_working_model(provider: str) -> Optional[str]:
    """The model a provider should be called with right now, or None."""
    models = get_all_working_models(provider)
    return models[0] if models else None


def warmup_model_cache():
    """
    Warm up model cache on startup (for production).
    Call this during app initialization to pre-populate cache.
    """
    logger.info("Warming up model cache...")
    for provider in _DISCOVERERS:
        try:
            models = get_all_working_models(provider)
            if models:
                logger.info("Cached %d %s models (best: %s)", len(models), provider, models[0])
        except Exception as e:
            logger.warning("%s cache warmup failed: %s", provider, e)
    logger.info("Model cache warmup complete")
