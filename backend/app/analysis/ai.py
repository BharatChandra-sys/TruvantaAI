# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
# Project: FactCheckAI � https://github.com/BharatChandra-sys/fake-news-extension
from __future__ import annotations

import os
import re
import json
import logging
import time
import requests
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from typing import List, Optional, Tuple

from app.analysis.model_registry import ModelCallError, judge_models, registry, try_models

logger = logging.getLogger(__name__)

# Module-level thread pool — created once, reused for every request
# Avoids the 20-50ms overhead of spawning/joining a pool per call
_POOL = ThreadPoolExecutor(max_workers=5, thread_name_prefix="ai-provider")

CEREBRAS_URL  = "https://api.cerebras.ai/v1/chat/completions"
GROQ_URL      = "https://api.groq.com/openai/v1/chat/completions"
# MiniMax M2.7 — 229B MoE, recursive self-improvement, SOTA real-world engineering
# OpenAI-compatible endpoint. Falls back to M2.7-highspeed for lower latency.
MINIMAX_URL   = "https://api.minimax.io/v1/chat/completions"
# OpenRouter — FREE tier with multiple models (Google Gemma 2 9B, Meta Llama 3.1 8B, etc)
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ── Structured JSON prompt ────────────────────────────────────
SYSTEM_PROMPT = """You are a professional fact-checker. Analyze the given claim and respond with ONLY a JSON object — no markdown, no extra text.

JSON format:
{
  "verdict": "fake" | "real" | "uncertain",
  "confidence": <float 0.0–1.0>,
  "explanation": "<3–5 sentence factual explanation>"
}

Rules:
- verdict must be exactly one of: fake, real, uncertain
- confidence is how certain you are (0.0 = no idea, 1.0 = certain)
- explanation must be factual, calm, and natural — no AI disclaimers
- Do NOT include markdown fences or any text outside the JSON"""

# ── Cached API keys (lazy init) ──────────────────────────
_KEYS: Optional[dict] = None


def _get_keys() -> dict:
    global _KEYS
    if _KEYS is None:
        _KEYS = {
            "cerebras":     os.getenv("CEREBRAS_API_KEY"),
            "groq":         os.getenv("GROQ_API_KEY"),
            "gemini":       os.getenv("GEMINI_API_KEY"),
            "minimax":      os.getenv("MINIMAX_API_KEY"),
            "openrouter":   os.getenv("OPENROUTER_API_KEY"),
            "gemini_proxy": os.getenv("GEMINI_WEB2API_URL", "https://factcheckai-gemini-proxy.onrender.com"),
        }
    return _KEYS


def _parse_structured(raw: str) -> dict:
    """Extract JSON from LLM response, handling minor formatting issues."""
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"No JSON found in response: {raw[:200]}")


def _verdict_to_score(verdict: str) -> float:
    """Convert structured verdict to a fake probability score."""
    v = verdict.lower().strip()
    if v == "fake":      return 0.85
    if v == "real":      return 0.15
    if v == "uncertain": return 0.5
    return 0.5


def _call_openai_compat(url: str, key: str, model: str, text: str,
                         timeout: int = 12, max_tokens: int = 500,
                         system: str = SYSTEM_PROMPT, user: Optional[str] = None) -> dict:
    """Shared helper for OpenAI-compatible chat completion endpoints."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user if user is not None else f"Claim: {text}"}
        ],
        "temperature": 0.1,
        "max_tokens": max_tokens,
    }
    
    # Keep reasoning short for a quick verdict. gpt-oss only accepts
    # low/medium/high; Qwen 3 can switch reasoning off entirely.
    if "gpt-oss" in model:
        payload["reasoning_effort"] = "low"
    elif "qwen" in model:
        payload["reasoning_effort"] = "none"
    
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )
    
    if r.status_code != 200:
        raise ModelCallError(r.status_code, r.text[:2000])   # full enough to classify (quota details come late)
    raw = r.json()["choices"][0]["message"]["content"].strip()
    return _parse_structured(raw)


def _call_cerebras(text: str) -> dict:
    from app.analysis.ai_config import get_api_keys, discover_cerebras_models
    
    keys = get_api_keys()
    key = keys.get("cerebras")
    if not key:
        raise ValueError("Cerebras API key missing")
    
    # Try to discover available models
    models = discover_cerebras_models(key)
    
    if not models:
        raise ValueError("Cerebras free tier exhausted (payment required)")
    
    return try_models("cerebras", models,
                      lambda model: _call_openai_compat(CEREBRAS_URL, key, model, text))


def _call_groq(text: str) -> dict:
    from app.analysis.ai_config import get_api_keys, discover_groq_models
    
    keys = get_api_keys()
    key = keys.get("groq")
    if not key:
        raise ValueError("Groq API key missing")
    
    # Try to discover available models
    models = discover_groq_models(key)
    
    return try_models("groq", models,
                      lambda model: _call_openai_compat(GROQ_URL, key, model, text, timeout=10))


def _post_json(url: str, payload: dict, timeout: int) -> dict:
    r = requests.post(url, headers={"Content-Type": "application/json"}, json=payload, timeout=timeout)
    if r.status_code != 200:
        raise ModelCallError(r.status_code, r.text[:2000])   # full enough to classify (quota details come late)
    return r.json()


def _call_google_generate(key: str, model: str, text: str, max_tokens: int = 300, timeout: int = 12,
                          system: str = SYSTEM_PROMPT, user: Optional[str] = None) -> dict:
    """Google AI Studio generateContent (Gemini and Gemma models)."""
    prompt = f"{system}\n\n{user if user is not None else f'Claim: {text}'}"
    data = _post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
        {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": max_tokens},
        },
        timeout,
    )
    raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    return _parse_structured(raw)


def _is_gemma(model: str) -> bool:
    return "gemma" in model.lower()


def _call_gemini(text: str) -> dict:
    """
    Gemini via the web2api proxy when it is reachable, otherwise Google AI
    Studio directly. AI Studio keys come as "AIza..." or, newer, "AQ...";
    both work with the official API.
    """
    from app.analysis.ai_config import get_api_keys, discover_gemini_proxy_models, discover_gemini_models

    keys = get_api_keys()
    key = keys.get("gemini")
    proxy_url = keys.get("gemini_proxy")
    if not key and not proxy_url:
        raise ValueError("Gemini API key and proxy both missing")

    errors = []
    if proxy_url and registry.provider_available("gemini_proxy"):
        def via_proxy(model):
            data = _post_json(f"{proxy_url}/v1/chat/completions", {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Claim: {text}"},
                ],
                "temperature": 0.1,
                "max_tokens": 300,
            }, 12)
            return _parse_structured(data["choices"][0]["message"]["content"].strip())
        try:
            return try_models("gemini_proxy", discover_gemini_proxy_models(proxy_url), via_proxy)
        except Exception as e:
            errors.append(str(e))

    if key:
        models = [m for m in discover_gemini_models(key) if not _is_gemma(m)]
        try:
            return try_models("gemini", models, lambda m: _call_google_generate(key, m, text), limit=2)
        except Exception as e:
            errors.append(str(e))

    raise ValueError("All Gemini models failed: " + "; ".join(errors)[:300])


def _call_minimax(text: str) -> dict:
    """
    MiniMax M2.7 — 229B MoE model, recursive self-improvement, SOTA real-world engineering.
    OpenAI-compatible endpoint at api.minimax.io.
    Falls back to MiniMax-M2.7-highspeed for lower latency if the flagship times out.
    """
    key = _get_keys()["minimax"]
    if not key:
        raise ValueError("MiniMax API key missing")

    for model in ["MiniMax-M2.7", "MiniMax-M2.7-highspeed"]:
        try:
            return _call_openai_compat(MINIMAX_URL, key, model, text,
                                       timeout=20, max_tokens=500)
        except Exception:
            continue
    raise ValueError("MiniMax M2.7 and M2.7-highspeed both failed")


def _call_gemma4(text: str) -> dict:
    """
    Google's open Gemma models, through the same AI Studio key as Gemini.
    Uses whichever Gemma models the key can see, largest and newest first.
    """
    from app.analysis.ai_config import discover_gemini_models

    key = _get_keys()["gemini"]
    if not key:
        raise ValueError("Gemma needs a Google AI Studio key")
    models = [m for m in discover_gemini_models(key) if _is_gemma(m)]
    return try_models("gemma", models,
                      lambda m: _call_google_generate(key, m, text, max_tokens=400, timeout=15), limit=2)


def _call_openrouter(text: str) -> dict:
    """
    OpenRouter — FREE tier with access to multiple free models.
    Tries only TOP 3 models for speed (nex-pro, ling-vl, liquid).
    """
    from app.analysis.ai_config import get_api_keys, discover_openrouter_models
    
    keys = get_api_keys()
    key = keys.get("openrouter")
    if not key:
        raise ValueError("OpenRouter API key missing")
    
    # Discover free models
    models = discover_openrouter_models(key)
    
    return try_models("openrouter", models,
                      lambda model: _call_openai_compat(OPENROUTER_URL, key, model, text, timeout=12))


def _call_huggingface(text: str) -> dict:
    """
    HuggingFace Inference API — 100% FREE, works without API key for public models.
    Uses Meta Llama 3.2 3B Instruct (small but capable).
    Optional: Get token at https://huggingface.co/settings/tokens for higher rate limits.
    """
    token = _get_keys().get("huggingface", "")
    prompt = f"{SYSTEM_PROMPT}\n\nClaim: {text}"
    
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        r = requests.post(
            HUGGINGFACE_URL,
            headers=headers,
            json={"inputs": prompt, "parameters": {"max_new_tokens": 300, "temperature": 0.1}},
            timeout=20  # HF can be slow on first request (model loading)
        )
        r.raise_for_status()
        raw = r.json()[0]["generated_text"]
        # Extract only the model's response (remove the prompt)
        if prompt in raw:
            raw = raw.replace(prompt, "").strip()
        return _parse_structured(raw)
    except Exception as e:
        raise ValueError(f"HuggingFace inference failed: {str(e)}")


def _ensemble_vote(results: List[dict]) -> dict:
    """
    Weighted ensemble voting across multiple LLM verdicts.
    
    Weights by model capability tier (based on 2026-09-22 testing):
    - Gemini 3.7 Flash (proxy): 2.5x - BEST (1.0 confidence, 100% success)
    - Groq gpt-oss-120b: 2.0x - GREAT (0.99 confidence, 120B reasoning)
    - Gemma 4 31B: 1.8x - GREAT (reasoning mode)
    - OpenRouter NEX Pro: 1.5x - GOOD (0.99 confidence)
    - Groq gpt-oss-20b: 1.3x - GOOD (0.99 confidence, fast)
    - Other Gemini models: 1.2x - GOOD
    - Other Groq models: 1.0x - OK
    - Other OpenRouter: 0.8x - OK
    
    Returns the consensus verdict with blended confidence and
    the explanation from the highest-weighted agreeing model.
    """
    if not results:
        return {"verdict": "uncertain", "confidence": 0.5, "explanation": ""}
    if len(results) == 1:
        return results[0]

    weights = {
        "gemini":     2.5,   # Gemini Proxy (3.7 Flash) - BEST (1.0 confidence, 2s)
        "groq":       2.0,   # Groq gpt-oss-120b - GREAT (0.99 confidence, 120B)
        "gemma4":     1.8,   # Gemma 4 31B - GREAT (reasoning mode)
        "openrouter": 1.5,   # OpenRouter NEX Pro - GOOD (0.99 confidence)
    }

    vote_scores = {"fake": 0.0, "real": 0.0, "uncertain": 0.0}
    total_weight = 0.0
    best_explanation = ""
    best_weight = 0.0

    for r in results:
        v = r.get("verdict", "uncertain").lower()
        conf = float(r.get("confidence", 0.5))
        src = r.get("_source", "unknown")
        w = weights.get(src, 1.0) * conf  # weight by model tier × confidence
        vote_scores[v] = vote_scores.get(v, 0.0) + w
        total_weight += w
        if w > best_weight and r.get("explanation"):
            best_weight = w
            best_explanation = r["explanation"]

    winner = max(vote_scores, key=vote_scores.get)
    winner_weight = vote_scores[winner]
    ensemble_confidence = (winner_weight / total_weight) if total_weight > 0 else 0.5
    # Clamp to [0.3, 0.97] — never be overconfident or underconfident
    ensemble_confidence = max(0.3, min(0.97, ensemble_confidence))

    return {
        "verdict": winner,
        "confidence": ensemble_confidence,
        "explanation": best_explanation,
    }


# How long to wait for more votes once one provider has answered, and the
# hard cap for the whole ensemble.
_GRACE_AFTER_FIRST_S = 3.0
_ENSEMBLE_TIMEOUT_S = 20.0


def _run_all_parallel(text: str):
    """
    Ask every configured provider in parallel and collect their verdicts.

    Returns as soon as one provider has answered and the others have had a
    short grace period to add their vote, so a slow or broken provider never
    holds up the result. Providers whose key was rejected are skipped
    entirely until the registry's hold expires.
    """
    keys = _get_keys()
    candidates = []
    if keys["gemini_proxy"] or keys["gemini"]:
        candidates.append(("gemini", _call_gemini))
    if keys["gemini"]:
        candidates.append(("gemma4", _call_gemma4))
    if keys["groq"]:
        candidates.append(("groq", _call_groq))
    if keys["openrouter"]:
        candidates.append(("openrouter", _call_openrouter))
    if keys["cerebras"]:
        candidates.append(("cerebras", _call_cerebras))

    registry_name = {"gemma4": "gemma"}
    providers = [(n, fn) for n, fn in candidates if registry.provider_available(registry_name.get(n, n))]
    if not providers:
        return [], {"all": "No API keys configured" if not candidates else "All providers on hold"}

    successes, errors = [], {}
    futures = {_POOL.submit(fn, text): name for name, fn in providers}
    pending = set(futures)
    deadline = time.monotonic() + _ENSEMBLE_TIMEOUT_S

    while pending:
        now = time.monotonic()
        limit = deadline if not successes else min(deadline, first_success_at + _GRACE_AFTER_FIRST_S)
        if now >= limit:
            break
        done, pending = wait(pending, timeout=limit - now, return_when=FIRST_COMPLETED)
        for future in done:
            name = futures[future]
            try:
                result = future.result()
                result["_source"] = name
                successes.append(result)
                if len(successes) == 1:
                    first_success_at = time.monotonic()
                logger.info("✅ %s answered (%s)", name, result.get("_model", "?"))
            except Exception as e:
                errors[name] = str(e)
                logger.warning("❌ %s failed: %s", name, str(e)[:160])

    for future in pending:          # still running: don't wait, just stop counting them
        future.cancel()
        errors[futures[future]] = "skipped (too slow)"
    return successes, errors


def run_ai_analysis(text: str):
    """
    Runs all configured LLM providers in parallel (Cerebras, Groq, Gemini,
    Gemma 4 31B-it, MiniMax M2.7) and returns an ensemble-voted verdict.

    If NO AI providers are available, falls back to rule-based analysis.

    Returns: (ai_fake_score: float | None, explanation: str)
    """
    # Try cache first
    try:
        from app.cache import partial_cache
        cached = partial_cache.get_ai_score(text)
        if cached is not None:
            logger.debug("AI analysis cache hit")
            return cached.get("score"), cached.get("explanation", "")
    except Exception as e:
        logger.debug("Cache lookup failed: %s", e)

    successes, errors = _run_all_parallel(text)

    # If AI providers available, use them
    if successes:
        ensemble = _ensemble_vote(successes)
        verdict = ensemble.get("verdict", "uncertain")
        llm_conf = float(ensemble.get("confidence", 0.5))
        explanation = ensemble.get("explanation", "")

        # Convert verdict → fake probability score
        score = _verdict_to_score(verdict)
        if verdict == "fake":
            score = max(score, llm_conf * 0.95)
        elif verdict == "real":
            score = min(score, 1.0 - llm_conf * 0.95)

        logger.info(
            "AI ensemble: verdict=%s conf=%.2f score=%.3f providers=%s errors=%s",
            verdict, llm_conf, score,
            [r.get("_source") for r in successes],
            list(errors.keys()) if errors else "none"
        )

        # Cache the result
        try:
            from app.cache import partial_cache
            partial_cache.set_ai_score(text, score, explanation)
        except Exception as e:
            logger.debug("Cache set failed: %s", e)

        return score, explanation

    # FALLBACK: NO AI PROVIDERS AVAILABLE
    # Use rule-based analysis as fallback
    logger.warning("No AI providers available, using rule-based fallback")
    
    # Simple rule-based fake news indicators
    text_lower = text.lower()
    fake_score = 0.5  # Start neutral
    indicators = []
    
    # Sensational keywords (increase fake score)
    sensational = ["shocking", "unbelievable", "you won't believe", "doctors hate", 
                   "miracle", "secret they don't want", "breaking", "exclusive"]
    for word in sensational:
        if word in text_lower:
            fake_score += 0.05
            indicators.append(f"sensational language: '{word}'")
    
    # All caps words (often clickbait)
    caps_words = [w for w in text.split() if w.isupper() and len(w) > 2]
    if len(caps_words) > 2:
        fake_score += 0.1
        indicators.append(f"{len(caps_words)} all-caps words")
    
    # Emotional manipulation
    emotional = ["outraged", "furious", "devastated", "terrified", "horrified"]
    for word in emotional:
        if word in text_lower:
            fake_score += 0.05
            indicators.append(f"emotional manipulation: '{word}'")
    
    # Clamp score to [0.3, 0.7] - rule-based shouldn't be too confident
    fake_score = max(0.3, min(0.7, fake_score))
    
    explanation = (
        f"AI analysis unavailable. Rule-based detection found: {', '.join(indicators) if indicators else 'no strong indicators'}. "
        f"Recommendation: Verify with trusted sources."
    )
    
    return fake_score, explanation


# ══════════════════════════════════════════════════════════════
# Grounded verdict: the model judges retrieved passages, not memory
# ══════════════════════════════════════════════════════════════

GROUNDED_PROMPT = """You are a professional fact-checker. Judge the claim using ONLY the numbered sources below. Today's date is {today}.

Respond with ONLY a JSON object, no markdown:
{{
  "verdict": "supported" | "refuted" | "uncertain",
  "confidence": <float 0.0-1.0>,
  "explanation": "<2-4 short sentences. Put [n] after each sentence the sources support, using the source numbers.>",
  "stances": {{"1": "support" | "refute" | "neutral", "2": ...}}
}}

Rules:
- "supported" means the sources show the claim is true; "refuted" means they show it is false; "uncertain" means they are mixed or do not settle it.
- Decide the verdict last, from your explanation: if your explanation says the claim is wrong, the verdict is "refuted".
- Base the verdict on the sources. Use general knowledge only to read them correctly, never as the only reason.
- A published fact-check rating is strong evidence, but only if it is about the same claim.
- Sources marked "low-reliability web result" are weak: never base the verdict on them alone.
- Give a stance for every source number. "neutral" means the source does not address the claim.
- Cite only source numbers that appear below, and only for sources that address the claim.
- Do not describe sources that are irrelevant; just mark them "neutral". Be calm and factual; no disclaimers."""

# Hedge: start with the fastest provider, add the others only if it is slow.
_HEDGE_AFTER_S = 2.0
_GROUNDED_TIMEOUT_S = 12.0
_CITATION = re.compile(r"\[(\d+)\]")


def _format_sources(passages: List[dict]) -> str:
    lines = []
    for i, p in enumerate(passages, 1):
        meta = ", ".join(x for x in (p.get("source"), p.get("published", "")[:10],
                                     "low-reliability web result" if p.get("low_trust") else "") if x)
        lines.append(f"[{i}] {p.get('title', '')[:160]} ({meta})\n{p.get('text', '')}")
    return "\n\n".join(lines)


def _grounded_providers(system: str, user: str):
    """(registry name, callable) per provider, fastest and most reliable first."""
    from app.analysis.ai_config import (discover_groq_models, discover_openrouter_models,
                                        discover_gemini_models, discover_cerebras_models)
    keys = _get_keys()
    out = []
    if keys["groq"]:
        out.append(("groq", lambda: try_models(
            "groq", judge_models(discover_groq_models(keys["groq"])),
            lambda m: _call_openai_compat(GROQ_URL, keys["groq"], m, "", timeout=10, max_tokens=700,
                                          system=system, user=user), limit=2)))
    if keys.get("cerebras"):
        out.append(("cerebras", lambda: try_models(
            "cerebras", judge_models(discover_cerebras_models(keys["cerebras"])),
            lambda m: _call_openai_compat(CEREBRAS_URL, keys["cerebras"], m, "", timeout=10, max_tokens=700,
                                          system=system, user=user), limit=2)))
    if keys["gemini"]:
        out.append(("gemini", lambda: try_models(
            "gemini", judge_models(m for m in discover_gemini_models(keys["gemini"]) if not _is_gemma(m)),
            lambda m: _call_google_generate(keys["gemini"], m, "", max_tokens=700, timeout=10,
                                            system=system, user=user),
            # Retired or no-free-quota models fail fast (404 / 429 limit 0) and are then
            # held; three tries let one check step past them to a working model.
            limit=3)))
    if keys["openrouter"]:
        out.append(("openrouter", lambda: try_models(
            "openrouter", judge_models(discover_openrouter_models(keys["openrouter"])),
            lambda m: _call_openai_compat(OPENROUTER_URL, keys["openrouter"], m, "", timeout=10,
                                          max_tokens=700, system=system, user=user), limit=1)))
    return [(n, fn) for n, fn in out if registry.provider_available(n)]


def _first_hedged(providers) -> Optional[dict]:
    """Run the first provider; if it hasn't answered in _HEDGE_AFTER_S, run the rest too."""
    if not providers:
        return None
    futures = {}
    start = time.monotonic()
    queue = list(providers)
    name, fn = queue.pop(0)
    futures[_POOL.submit(fn)] = name
    hedged = False
    while futures:
        elapsed = time.monotonic() - start
        if elapsed >= _GROUNDED_TIMEOUT_S:
            break
        wait_for = _GROUNDED_TIMEOUT_S - elapsed if hedged else max(0.0, _HEDGE_AFTER_S - elapsed)
        done, _ = wait(list(futures), timeout=wait_for, return_when=FIRST_COMPLETED)
        for f in done:
            src = futures.pop(f)
            try:
                result = f.result()
                result["_source"] = src
                for other in futures:
                    other.cancel()
                return result
            except Exception as e:
                logger.warning("grounded %s failed: %s", src, str(e)[:160])
        if not hedged and (not futures or time.monotonic() - start >= _HEDGE_AFTER_S):
            hedged = True
            for name, fn in queue:
                futures[_POOL.submit(fn)] = name
            queue = []
    return None


KNOWLEDGE_PROMPT = """You are a professional fact-checker. No sources could be found for this claim, so judge it from well-established knowledge. Today's date is {today}.

Respond with ONLY a JSON object, no markdown:
{{
  "verdict": "true" | "false" | "uncertain",
  "confidence": <float 0.0-1.0>,
  "explanation": "<1-3 short sentences giving the established fact the verdict rests on>"
}}

Rules:
- "true" means the claim is correct, "false" means it is wrong. Decide it last, from your explanation.
- Answer "true" or "false" only for settled facts: science, history, geography, well-documented events.
- Answer "uncertain" for anything recent, local, about a specific person's current status, a statistic you are not sure of, or that you cannot place. A wrong answer is worse than "uncertain".
- No citations, no disclaimers, no mention of sources. Be calm and factual."""

# The prompts ask for words that can't be misread: models asked for "real"/"fake"
# sometimes answered "real" meaning "the sources are real" while explaining that
# the claim is false. Internally the verdict stays real / fake / uncertain.
_VERDICT_WORDS = {"supported": "real", "true": "real", "real": "real",
                  "refuted": "fake", "false": "fake", "fake": "fake"}


def _verdict_label(raw) -> str:
    return _VERDICT_WORDS.get(str(raw or "").lower().strip(), "uncertain")


# A verdict from the model's own knowledge is never presented as near-certain.
KNOWLEDGE_MAX_CONFIDENCE = 0.7


def run_knowledge_analysis(claim: str) -> Optional[dict]:
    """
    Verdict when no source addresses the claim: the model's established
    knowledge, capped in confidence. Returns None when no provider answers.
    """
    from datetime import date
    system = KNOWLEDGE_PROMPT.format(today=date.today().isoformat())
    result = _first_hedged(_grounded_providers(system, f"Claim: {claim}"))
    if not result:
        return None
    verdict = _verdict_label(result.get("verdict"))
    try:
        conf = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
    except (TypeError, ValueError):
        conf = 0.5
    if verdict == "uncertain":
        conf = 0.5
    else:
        conf = round(min(KNOWLEDGE_MAX_CONFIDENCE, max(0.55, conf)), 2)
    return {
        "verdict": verdict,
        "confidence": conf,
        "explanation": _CITATION.sub("", str(result.get("explanation", ""))).strip(),
        "ai_score": _verdict_to_score(verdict),
        "model": result.get("_model") or result.get("_source"),
    }


def run_grounded_analysis(claim: str, passages: List[dict]) -> Optional[dict]:
    """
    Verdict from retrieved passages. Returns None when no provider answers,
    otherwise: verdict, confidence, explanation (with [n] citations),
    stances {index: support|refute|neutral}, ai_score (fake probability), model.
    """
    if not passages:
        return None
    from datetime import date
    system = GROUNDED_PROMPT.format(today=date.today().isoformat())
    user = f"Claim: {claim}\n\nSources:\n{_format_sources(passages)}"

    result = _first_hedged(_grounded_providers(system, user))
    if not result:
        return None

    n = len(passages)
    verdict = _verdict_label(result.get("verdict"))
    try:
        conf = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
    except (TypeError, ValueError):
        conf = 0.5
    # Drop citations to sources that were never given.
    explanation = _CITATION.sub(lambda m: m.group(0) if 1 <= int(m.group(1)) <= n else "",
                                str(result.get("explanation", ""))).strip()
    stances = {}
    for k, v in (result.get("stances") or {}).items():
        try:
            i = int(k)
        except (TypeError, ValueError):
            continue
        if 1 <= i <= n and v in ("support", "refute", "neutral"):
            stances[i] = v

    score = _verdict_to_score(verdict)
    if verdict == "fake":
        score = max(score, conf * 0.95)
    elif verdict == "real":
        score = min(score, 1.0 - conf * 0.95)
    return {
        "verdict": verdict,
        "confidence": conf,
        "explanation": explanation,
        "stances": stances,
        "ai_score": score,
        "model": result.get("_model") or result.get("_source"),
    }
