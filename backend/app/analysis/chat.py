# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
# Project: FactCheckAI � https://github.com/BharatChandra-sys/fake-news-extension
import os
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
load_dotenv(_env_path)

# Import central AI config for dynamic model discovery
from app.analysis.model_registry import ModelCallError, registry, try_models
from app.analysis.ai_config import (
    get_api_keys, get_all_working_models, get_first_working_model,
    CEREBRAS_URL, GROQ_URL, MINIMAX_URL, OPENROUTER_URL, GEMINI_URL_BASE
)

CHAT_SYSTEM = (
    "You are a helpful, knowledgeable assistant specializing in media literacy and fact-checking. "
    "Answer questions clearly and concisely. Be friendly and factual. Never fabricate sources or statistics. "
    "When discussing news or claims, always encourage users to verify information from multiple trusted sources."
)

CLAIM_DETECT_PROMPT = (
    "Classify the following input as either 'claim' or 'other'.\n"
    "A 'claim' is a statement that asserts something as true or false and can be fact-checked "
    "(e.g. news headlines, assertions about events, scientific claims, political statements).\n"
    "'other' includes greetings, questions asking for information, opinions, casual conversation, "
    "or anything that is not a verifiable factual assertion.\n\n"
    "Reply with ONLY one word: claim or other.\n\n"
    "Input: {text}"
)

# ══════════════════════════════════════════════════════════
# 🚀 OPTIMIZATION: Pattern-based responses (no AI needed)
# ══════════════════════════════════════════════════════════

# Common greetings and simple queries - instant responses
QUICK_RESPONSES = {
    r'^(hi|hello|hey|greetings)[\s!.]*$': "Hello! I'm TruvantaAI, your fact-checking assistant. How can I help you today?",
    r'^(how are you|how\'s it going|what\'s up)[\s?!.]*$': "I'm functioning well, thanks! I'm here to help you verify claims and combat misinformation. What would you like to check?",
    r'^(thanks|thank you|thx)[\s!.]*$': "You're welcome! Feel free to ask if you need anything else.",
    r'^(bye|goodbye|see you)[\s!.]*$': "Goodbye! Stay informed and keep questioning what you read online.",
    r'^(who are you|what are you)[\s?!.]*$': "I'm TruvantaAI, an AI-powered fact-checking assistant. I help verify claims, detect fake news, and provide evidence-based analysis.",
    r'^(help|what can you do)[\s?!.]*$': "I can help you:\n• Fact-check claims and news articles\n• Detect misinformation and fake news\n• Provide evidence from trusted sources\n• Analyze manipulation tactics\n\nJust share a claim or article with me!",
}

def _quick_response(text: str) -> str:
    """Check if input matches common patterns for instant response."""
    text_lower = text.lower().strip()
    for pattern, response in QUICK_RESPONSES.items():
        if re.match(pattern, text_lower, re.IGNORECASE):
            return response
    return None


# ══════════════════════════════════════════════════════════
# 🎯 OPTIMIZATION: TF-IDF claim detection (local, fast)
# ══════════════════════════════════════════════════════════

def _tfidf_is_claim(text: str) -> bool:
    """Use local TF-IDF model to detect if text is a claim (fast, no API calls)."""
    try:
        import joblib
        import os
        
        # Load TF-IDF model
        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "model.joblib")
        vectorizer_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "vectorizer.joblib")
        
        if not os.path.exists(model_path) or not os.path.exists(vectorizer_path):
            return None  # Models not available, fallback to AI
        
        model = joblib.load(model_path)
        vectorizer = joblib.load(vectorizer_path)
        
        # Heuristic rules first (very fast)
        text_lower = text.lower().strip()
        
        # Clearly NOT claims (questions, greetings, opinions)
        if any(text_lower.startswith(prefix) for prefix in [
            'how', 'what', 'why', 'when', 'where', 'who', 'can you', 'could you',
            'please', 'hi', 'hello', 'hey', 'thanks', 'i think', 'in my opinion'
        ]):
            return False
        
        # Too short to be a claim
        if len(text.split()) < 4:
            return False
        
        # Has question mark = question, not claim
        if '?' in text:
            return False
        
        # Vectorize and predict
        X = vectorizer.transform([text])
        prediction = model.predict(X)[0]
        
        # If TF-IDF predicts fake (>0.5) or real (<0.5), it's likely a claim
        # If confidence is very low, it might be conversational text
        proba = model.predict_proba(X)[0]
        max_proba = max(proba)
        
        # High confidence = claim, low confidence = not a claim
        return max_proba > 0.6  # Require 60% confidence to consider it a claim
        
    except Exception as e:
        import logging
        logging.debug(f"TF-IDF claim detection failed: {e}")
        return None  # Fallback to AI


def _get_keys():
    """Wrapper for backward compatibility."""
    return get_api_keys()


def _call_openai_compat(url: str, key: str, model: str, messages: list, max_tokens=400, temperature=0.7) -> str:
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
        timeout=15
    )
    if r.status_code != 200:
        raise ModelCallError(r.status_code, r.text[:300])
    return r.json()["choices"][0]["message"]["content"].strip()


def _registry_fns(messages: list, **kwargs) -> list:
    """
    One entry per OpenAI-compatible provider. Each tries that provider's
    best-ranked models and reports the outcome, so dead models are skipped
    next time and newly released ones get picked up.
    """
    keys = _get_keys()
    fns = []
    for name, url, key_name in (("OpenRouter", OPENROUTER_URL, "openrouter"),
                                ("Groq", GROQ_URL, "groq"),
                                ("Cerebras", CEREBRAS_URL, "cerebras")):
        key = keys.get(key_name)
        if not key or not registry.provider_available(key_name):
            continue
        fns.append((name, lambda u=url, k=key, p=key_name: try_models(
            p, get_all_working_models(p),
            lambda m: _call_openai_compat(u, k, m, messages, **kwargs), limit=2)))
    return fns


def _call_gemini(messages: list, max_tokens=400, temperature=0.7) -> str:
    key = _get_keys()["gemini"]
    if not key:
        raise ValueError("Gemini API key missing")
    
    # Use dynamic model discovery - try first available model
    from app.analysis.ai_config import discover_gemini_models
    models = discover_gemini_models(key)
    if not models:
        models = ["gemini-1.5-flash", "gemini-1.5-pro"]
    
    contents = []
    system_text = ""
    for m in messages:
        if m["role"] == "system":
            system_text = m["content"]
            continue
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    if contents and contents[0]["role"] == "user" and system_text:
        contents[0]["parts"][0]["text"] = system_text + "\n\n" + contents[0]["parts"][0]["text"]
    
    # Try models until one works
    for model in models[:3]:
        try:
            url = f"{GEMINI_URL_BASE}/{model}:generateContent"
            r = requests.post(
                f"{url}?key={key}",
                headers={"Content-Type": "application/json"},
                json={"contents": contents, "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens}},
                timeout=12
            )
            r.raise_for_status()
            return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            if model == models[-1] or model == models[2]:  # Last attempt
                raise
            continue
    raise ValueError("All Gemini models failed")


def _call_minimax_chat(messages: list, max_tokens=400, temperature=0.7) -> str:
    """MiniMax M2.7 for chat — fast, high quality, OpenAI-compatible."""
    key = _get_keys()["minimax"]
    if not key:
        raise ValueError("MiniMax API key missing")
    # Try M2.7-highspeed first for chat (lower latency), fall back to M2.7
    for model in ["MiniMax-M2.7-highspeed", "MiniMax-M2.7"]:
        try:
            r = requests.post(
                MINIMAX_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
                timeout=15
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            continue
    raise ValueError("MiniMax chat failed")


def _first_success(fn_list):
    """Run list of (name, callable) in parallel, return the first success
    without waiting for the slower ones to finish."""
    if not fn_list:
        raise RuntimeError("No AI providers configured")
    errors = []
    executor = ThreadPoolExecutor(max_workers=len(fn_list))
    try:
        futures = {executor.submit(fn): name for name, fn in fn_list}
        for future in as_completed(futures):
            try:
                return future.result()
            except Exception as e:
                errors.append(f"{futures[future]}: {e}")
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    raise RuntimeError(" | ".join(errors))


def is_claim(text: str) -> bool:
    """
    Optimized 3-tier detection:
    1. Quick pattern check (instant, no compute)
    2. Local TF-IDF model (fast, ~1ms, no API)
    3. AI fallback (slow, only if needed)
    """
    import logging
    
    # Tier 1: Quick pattern check
    quick_resp = _quick_response(text)
    if quick_resp:
        logging.info(f"[Claim Detection] Pattern match - NOT a claim (quick response available)")
        return False
    
    # Tier 2: Local TF-IDF claim detection
    tfidf_result = _tfidf_is_claim(text)
    if tfidf_result is not None:
        logging.info(f"[Claim Detection] TF-IDF model - {'IS' if tfidf_result else 'NOT'} a claim (local, 1ms)")
        return tfidf_result
    
    # Tier 3: AI fallback (only if TF-IDF unavailable or uncertain)
    logging.info(f"[Claim Detection] Falling back to AI (TF-IDF unavailable)")
    
    prompt = CLAIM_DETECT_PROMPT.format(text=text)
    messages = [{"role": "user", "content": prompt}]
    keys = _get_keys()

    fns = _registry_fns(messages, max_tokens=5, temperature=0)
    if keys["gemini"]:
        fns.append(("Gemini", lambda: _call_gemini(messages, max_tokens=5, temperature=0)))
    if keys["minimax"]:
        fns.append(("MiniMax", lambda: _call_minimax_chat(messages, max_tokens=5, temperature=0)))

    try:
        result = _first_success(fns)
        return result.strip().lower().startswith("claim")
    except Exception as e:
        # Log the error for debugging
        logging.warning(f"All AI providers failed for claim detection: {e}")
        # Default: treat as chat (not claim) if all AI providers fail
        return False


def run_chat(message: str, history: list) -> str:
    """
    Optimized chat with instant responses for common queries.
    """
    import logging
    
    # Check for instant response (no AI needed)
    quick_resp = _quick_response(message)
    if quick_resp:
        logging.info(f"[Chat] Quick response match - no AI call needed")
        return quick_resp
    
    # Build full conversation for AI
    msgs = [{"role": "system", "content": CHAT_SYSTEM}]
    for h in history[-6:]:
        msgs.append({"role": h["role"], "content": h["content"]})
    msgs.append({"role": "user", "content": message})

    keys = _get_keys()
    fns = _registry_fns(msgs)
    if keys["gemini"]:
        fns.append(("Gemini", lambda: _call_gemini(msgs)))
    if keys["minimax"]:
        fns.append(("MiniMax", lambda: _call_minimax_chat(msgs)))

    try:
        return _first_success(fns)
    except Exception as e:
        logging.warning(f"All AI providers failed for chat: {e}")
        return "I'm having trouble connecting right now. Please try again in a moment."
