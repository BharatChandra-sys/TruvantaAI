# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
# Project: FactCheckAI � https://github.com/BharatChandra-sys/fake-news-extension
"""
Level 70 — Cross-Encoder Evidence Reranking

Reranks NewsAPI and Tavily articles by relevance to the claim.

Relevance comes from the local cross-encoder in app/retrieval/reranker.py:
one call scores every article in milliseconds and gives the same scores on
every run. The LLM then reads only the articles that are kept, for their
stance, which replaces the simple keyword stance classifier. Without a local
model, the LLM scores relevance and stance for every article, as before.
"""
import logging
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

_RERANK_PROMPT = """Given this claim and news article, score the article's relevance and stance.

Claim: {claim}

Article title: {title}
Article description: {description}

Respond with ONLY a JSON object:
{{"relevance": <0.0-1.0>, "stance": "support"|"contradict"|"neutral", "reason": "<10 words max>"}}"""


def _score_article(claim: str, article: dict) -> Optional[dict]:
    """Score a single article against the claim using LLM (dynamic models)."""
    try:
        from app.analysis.chat import _call_openai_compat, _call_gemini, _get_keys, _first_success
        from app.analysis.ai_config import discover_cerebras_models, discover_groq_models, CEREBRAS_URL, GROQ_URL
        import json, re

        keys = _get_keys()
        prompt = _RERANK_PROMPT.format(
            claim=claim[:300],
            title=article.get("title", "")[:200],
            description=article.get("description", "")[:300],
        )
        messages = [{"role": "user", "content": prompt}]

        fns = []
        
        # Try Cerebras with dynamic model discovery
        if keys.get("cerebras"):
            cerebras_models = discover_cerebras_models(keys["cerebras"])
            for model in cerebras_models[:2]:
                try:
                    fns.append((f"Cerebras-{model}", lambda m=model: _call_openai_compat(
                        CEREBRAS_URL,
                        keys["cerebras"], m, messages, max_tokens=80, temperature=0
                    )))
                except Exception:
                    continue
                    
        # Try Groq with dynamic model discovery
        if keys.get("groq"):
            groq_models = discover_groq_models(keys["groq"])
            for model in groq_models[:2]:
                try:
                    fns.append((f"Groq-{model}", lambda m=model: _call_openai_compat(
                        GROQ_URL,
                        keys["groq"], m, messages, max_tokens=80, temperature=0
                    )))
                except Exception:
                    continue

        if not fns:
            return None

        raw = _first_success(fns)
        raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return {
                "relevance": float(data.get("relevance", 0.5)),
                "stance":    data.get("stance", "neutral"),
                "reason":    data.get("reason", ""),
            }
    except Exception as e:
        logger.debug("Cross-encoder scoring failed: %s", e)
    return None


def _article_text(article: dict) -> str:
    """What the cross-encoder reads: the headline and whatever summary the source gave."""
    summary = article.get("description") or article.get("snippet") or article.get("content") or ""
    return f"{article.get('title', '')}. {summary}".strip(" .")


def _llm_stances(claim: str, articles: list) -> None:
    """Set each article's stance from the LLM, in place; articles it can't read keep theirs."""
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(_score_article, claim, a): a for a in articles}
        for future in as_completed(futures):
            try:
                result = future.result()
            except Exception:
                continue
            if result:
                futures[future]["stance"]        = result["stance"]  # override keyword stance
                futures[future]["stance_reason"] = result["reason"]


def _rerank_with_llm(claim: str, articles: list, top_k: int) -> list:
    """Relevance and stance for every article from the LLM: the path without a local model."""
    scored = []
    # Run scoring in parallel — max 3 concurrent LLM calls
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(_score_article, claim, a): i for i, a in enumerate(articles)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                score = future.result()
                if score:
                    articles[idx]["relevance_score"] = score["relevance"]
                    articles[idx]["stance"]          = score["stance"]  # override keyword stance
                    articles[idx]["stance_reason"]   = score["reason"]
                    scored.append((score["relevance"], idx, articles[idx]))
                else:
                    scored.append((0.5, idx, articles[idx]))
            except Exception:
                scored.append((0.5, idx, articles[idx]))

    # Sort by relevance descending; ties keep the original order.
    scored.sort(key=lambda x: (-x[0], x[1]))
    return [a for _, _, a in scored[:top_k]]


def rerank_articles(claim: str, articles: list, top_k: int = 5) -> list:
    """
    Rerank articles by relevance to the claim and return the top_k, each with
    relevance_score (0-1) and an LLM stance where a provider answered.

    The local cross-encoder scores relevance when available, so only the top_k
    articles cost an LLM call; otherwise the LLM scores every article.
    Falls back to the original order if neither is available.
    """
    if not articles or len(articles) <= 1:
        return articles

    # Only rerank if we have more articles than top_k (otherwise no point)
    if len(articles) <= top_k:
        return articles

    from app.retrieval.reranker import score
    scores = score(claim, [_article_text(a) for a in articles])
    if scores is None:
        reranked = _rerank_with_llm(claim, articles, top_k)
    else:
        for a, s in zip(articles, scores):
            a["relevance_score"] = s
        # Stable sort: ties keep the search engine's order.
        reranked = sorted(articles, key=lambda a: a["relevance_score"], reverse=True)[:top_k]
        _llm_stances(claim, reranked)

    logger.debug("Cross-encoder reranked %d → %d articles", len(articles), len(reranked))
    return reranked
