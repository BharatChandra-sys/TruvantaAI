# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
# Project: FactCheckAI � https://github.com/BharatChandra-sys/fake-news-extension
"""
News evidence fetching with:
- Brave Search API (primary, real-time) with NewsAPI fallback
- Publisher bias weighting
- Retry + exponential backoff
- Cross-encoder reranking
"""
import os
import re
import time
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from app.analysis.credibility import get_trust_score, get_trust_label
from app.analysis.publisher_bias import get_bias_label, get_bias_weight

logger = logging.getLogger(__name__)

NEWS_API_KEY   = os.getenv("NEWS_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
FACTCHECK_KEY  = os.getenv("GOOGLE_FACTCHECK_API_KEY")
NEWS_API_URL   = "https://newsapi.org/v2/everything"
FACTCHECK_URL  = "https://factchecktools.googleapis.com/v1alpha1/claims:search"

# ── Reusable session with retry ───────────────────────────────
# No retry on 429: a rate-limited source won't recover within one request,
# and backing off only delays the answer.
_retry_strategy = Retry(
    total=1,
    backoff_factor=0.3,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET"],
)
_adapter = HTTPAdapter(max_retries=_retry_strategy)
_session = requests.Session()
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)

TRUSTED_SOURCES = {
    "reuters", "bbc news", "bbc", "associated press", "ap news",
    "the verge", "medical news today", "nature", "who", "cdc",
    "the guardian", "the new york times", "washington post",
    "nbc news", "abc news", "cbs news", "npr", "pbs",
    "bloomberg", "financial times", "the economist",
    "al jazeera", "france 24", "dw news", "afp",
    "ndtv", "the hindu", "hindustan times", "india today",
    "times of india", "press trust of india", "ani",
    "snopes", "factcheck.org", "politifact", "fullfact",
}

_SUPPORT_WORDS = re.compile(
    r"\b(confirm|confirmed|verif|true|accurate|correct|real|legitimate|"
    r"evidence shows|study finds|research confirms|officials say|"
    r"according to|report shows|data shows|proves|proven)\b",
    re.IGNORECASE,
)
_CONTRADICT_WORDS = re.compile(
    r"\b(false|fake|debunk|mislead|misinform|incorrect|wrong|"
    r"no evidence|unverified|disputed|claim is|rumor|hoax|"
    r"fact.?check|not true|baseless|fabricat|manipulat)\b",
    re.IGNORECASE,
)


def _stance(title: str, description: str) -> str:
    blob = f"{title} {description or ''}".lower()
    s = len(_SUPPORT_WORDS.findall(blob))
    c = len(_CONTRADICT_WORDS.findall(blob))
    if c > s:
        return "contradict"
    if s > c:
        return "support"
    return "neutral"


def _consistency_score(articles: list) -> float:
    """Trust + bias weighted consistency score."""
    support    = sum(
        a.get("trust_score", 0.5) * get_bias_weight(a.get("url", ""))
        for a in articles if a.get("stance") == "support"
    )
    contradict = sum(
        a.get("trust_score", 0.5) * get_bias_weight(a.get("url", ""))
        for a in articles if a.get("stance") == "contradict"
    )
    total = support + contradict
    if total == 0:
        return 0.5
    return round(support / total, 2)


# ClaimReview ratings vary by publisher ("False", "Pants on Fire", "Mostly true",
# "Misleading"...). Map the wording onto the stance used by the score.
_RATING_CONTRADICT = re.compile(
    r"\b(false|fake|pants on fire|incorrect|misleading|mislead|fabricat|baseless|"
    r"no evidence|not true|wrong|debunk|hoax|scam|distort|exaggerat|unsupported|satire)",
    re.IGNORECASE,
)
_RATING_SUPPORT = re.compile(r"\b(true|correct|accurate|confirmed|legit|real)\b", re.IGNORECASE)
_STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "on", "and", "or", "is", "are", "was", "were", "be",
    "it", "that", "this", "with", "for", "as", "by", "at", "from", "has", "have", "had", "not",
    "only", "can", "will", "its", "their", "his", "her", "they", "we", "you",
}


def _content_words(s: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in _STOPWORDS and len(w) > 2}


def _rating_stance(rating: str) -> str:
    rating = rating or ""
    mixed = re.search(r"\b(mostly|partly|half)[\s-]+(false|true)\b", rating, re.IGNORECASE)
    if mixed:
        return "contradict" if mixed.group(2).lower() == "false" else "support"
    if _RATING_CONTRADICT.search(rating):
        return "contradict"
    if _RATING_SUPPORT.search(rating):
        return "support"
    return "neutral"


def _fetch_factcheck_evidence(text: str) -> list:
    """
    Published fact-checks (ClaimReview) from Google Fact Check Tools.
    Free with an API key; returns professional verdicts with links.
    Only reviews whose claim actually overlaps the user's claim are kept.
    """
    if not FACTCHECK_KEY:
        return []
    try:
        res = _session.get(
            FACTCHECK_URL,
            params={"query": text[:200], "key": FACTCHECK_KEY, "languageCode": "en", "pageSize": 10},
            timeout=6,
        )
        if res.status_code != 200:
            logger.warning("Fact Check API returned %s", res.status_code)
            return []
        claim_words = _content_words(text)
        articles = []
        for claim in res.json().get("claims", []):
            overlap = claim_words & _content_words(claim.get("text", ""))
            if not claim_words or len(overlap) / len(claim_words) < 0.4:
                continue
            for review in claim.get("claimReview", [])[:2]:
                url = review.get("url") or ""
                if not url:
                    continue
                rating = review.get("textualRating") or ""
                publisher = (review.get("publisher") or {}).get("name") or ""
                articles.append({
                    "title":       review.get("title") or claim.get("text", ""),
                    "url":         url,
                    "source":      publisher,
                    "stance":      _rating_stance(rating),
                    "rating":      rating,
                    "review_date": review.get("reviewDate", ""),
                    "trust_score": max(get_trust_score(url), 0.85),   # professional fact-checkers
                    "trust_label": get_trust_label(url),
                    "bias_label":  get_bias_label(url),
                    "kind":        "fact_check",
                })
        return articles[:4]
    except Exception as e:
        logger.warning("Fact Check API error: %s", e)
        return []


def _search_evidence(text: str):
    """General web/news evidence: Tavily first, then NewsAPI."""
    if TAVILY_API_KEY:
        try:
            from app.analysis.brave_search import fetch_brave_evidence
            score, urls, articles = fetch_brave_evidence(text)
            if articles:
                return score, urls, articles
        except Exception as e:
            logger.warning("Web search failed, falling back to NewsAPI: %s", e)
    return _fetch_newsapi_evidence(text)


def fetch_evidence(text: str):
    """
    Primary entry point. Published fact-checks and general search run in
    parallel; their articles are merged, fact-checks first.
    Returns: (evidence_score, urls, articles). Cached for 1 hour.
    """
    try:
        from app.cache import partial_cache
        cached = partial_cache.get_evidence(text)
        if cached is not None:
            logger.debug("Evidence cache hit")
            return cached.get("score"), cached.get("urls", []), cached.get("articles", [])
    except Exception as e:
        logger.debug("Cache lookup failed: %s", e)

    from concurrent.futures import ThreadPoolExecutor
    pool = ThreadPoolExecutor(max_workers=2)
    try:
        fc_future = pool.submit(_fetch_factcheck_evidence, text)
        search_future = pool.submit(_search_evidence, text)
        fact_checks = fc_future.result()
        search_score, search_urls, search_articles = search_future.result()
    finally:
        pool.shutdown(wait=False)

    seen = set()
    articles = []
    for a in fact_checks + (search_articles or []):
        if a.get("url") and a["url"] not in seen:
            seen.add(a["url"])
            articles.append(a)
    articles = articles[:6]

    if articles:
        score = _consistency_score(articles)
        if not fact_checks:
            score = round(min(1.0, score + min(len(articles) / 5, 0.15)), 2)
        urls = [a["url"] for a in articles]
    else:
        # Nothing relevant found is "unknown", not "unsupported": returning a
        # low score here would push every unsourced claim towards "fake".
        score, urls = None, []

    if score is not None:
        try:
            from app.cache import partial_cache
            partial_cache.set_evidence(text, {"score": score, "urls": urls, "articles": articles})
        except Exception as e:
            logger.debug("Cache set failed: %s", e)
    return score, urls, articles


def _fetch_newsapi_evidence(text: str):
    """
    Returns:
        evidence_score (float | None)
        evidence_sources (list[str])
        evidence_articles (list[dict])
    """
    if not NEWS_API_KEY:
        return None, [], []

    params = {
        "q":        text[:100],
        "language": "en",
        "pageSize": 10,
        "sortBy":   "relevancy",
        "apiKey":   NEWS_API_KEY,
    }

    try:
        t0  = time.perf_counter()
        res = _session.get(NEWS_API_URL, params=params, timeout=6)
        elapsed = round((time.perf_counter() - t0) * 1000)

        if res.status_code != 200:
            logger.warning("NewsAPI returned %s in %sms", res.status_code, elapsed)
            return None, [], []

        logger.debug("NewsAPI OK in %sms", elapsed)
        articles = res.json().get("articles", [])
        if not articles:
            return 0.0, [], []

        trusted_articles = []
        all_urls = []

        for a in articles:
            url      = a.get("url") or ""
            title    = a.get("title") or ""
            desc     = a.get("description") or ""
            src      = a.get("source", {})
            src_id   = (src.get("id") or "").lower().strip()
            src_name = (src.get("name") or "").lower().strip()

            if url and url != "[Removed]":
                all_urls.append(url)

            if src_id in TRUSTED_SOURCES or src_name in TRUSTED_SOURCES:
                stance = _stance(title, desc)
                trust  = get_trust_score(url)
                trusted_articles.append({
                    "title":       title,
                    "url":         url,
                    "source":      src.get("name", ""),
                    "stance":      stance,
                    "trust_score": trust,
                    "trust_label": get_trust_label(url),
                    "bias_label":  get_bias_label(url),
                })

        if not trusted_articles:
            return None, all_urls[:3], []

        # Cross-encoder reranking — semantically rerank by claim relevance
        try:
            from app.analysis.cross_encoder import rerank_articles
            trusted_articles = rerank_articles(text, trusted_articles, top_k=5)
        except Exception as e:
            logger.debug("Cross-encoder reranking skipped: %s", e)

        score = _consistency_score(trusted_articles)
        coverage_bonus = min(len(trusted_articles) / 5, 0.15)
        score = round(min(1.0, score + coverage_bonus), 2)

        urls = [a["url"] for a in trusted_articles if a["url"]]
        return score, urls[:5], trusted_articles[:5]

    except requests.exceptions.Timeout:
        logger.warning("NewsAPI timed out after 6s")
        return None, [], []
    except Exception as e:
        # Not the exception text: it contains the request URL, API key included.
        logger.warning("NewsAPI error: %s", type(e).__name__)
        return None, [], []
