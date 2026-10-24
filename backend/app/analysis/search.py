# Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
# Licensed under the Apache License, Version 2.0
# SPDX-License-Identifier: Apache-2.0
"""
Evidence search and scraping, built for speed on free sources.

Every source runs in parallel under one hard deadline; whatever has arrived
by then is used and the rest is abandoned (no retries inside the window).
Web results are scraped as soon as they arrive, and only the paragraphs that
overlap the claim are kept, so the verdict model reads evidence, not pages.

Sources (all free):
  - Google Fact Check Tools  published fact-checks (ClaimReview), needs a key
  - Wikipedia                search + intro extracts in a single call
  - DuckDuckGo (ddgs)        web and news results, no key
  - GDELT DOC 2.0            recent news, no key (often slow, so short timeout)
  - Tavily                   only if TAVILY_API_KEY is valid (1,000/month free)
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from typing import Callable, Dict, List, Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

DEADLINE_S = 3.5            # whole search + scrape budget
ENOUGH_AFTER_S = 2.0        # after this, stop early once we have enough evidence
ENOUGH_PASSAGES = 5
SCRAPE_TIMEOUT_S = 1.8      # per page
SCRAPE_MAX_BYTES = 400_000  # stop reading big pages early
SCRAPE_PAGES = 3            # pages scraped per check
MAX_PASSAGES = 8            # passages handed to the verdict model
PASSAGE_CHARS = 600

USER_AGENT = "TruvantaFactCheck/2.6 (+https://github.com/BharatChandra-sys/TruvantaAI)"
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/141.0 Safari/537.36")

# Shared pool: search and scrape tasks of concurrent requests interleave here.
_POOL = ThreadPoolExecutor(max_workers=16, thread_name_prefix="search")
_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})

# Sites whose pages add nothing as evidence or block scrapers.
_SKIP_SCRAPE = ("youtube.com", "tiktok.com", "facebook.com", "instagram.com", "x.com",
                "twitter.com", "reddit.com", "pinterest.", "r.search.yahoo.com", "msn.com")

_STOP = {
    "the", "a", "an", "of", "to", "in", "on", "and", "or", "is", "are", "was", "were", "be", "been",
    "it", "that", "this", "with", "for", "as", "by", "at", "from", "has", "have", "had", "not", "only",
    "can", "will", "its", "their", "his", "her", "they", "we", "you", "than", "into", "about", "after",
    "before", "more", "most", "very", "also", "just", "does", "did", "do", "which", "who", "what",
}

# ── Source health: a source that rejects its key is skipped for a while ─────
_disabled: Dict[str, float] = {}
_disabled_lock = threading.Lock()


def _source_on(name: str) -> bool:
    with _disabled_lock:
        return _disabled.get(name, 0) <= time.time()


def _disable(name: str, seconds: float, why: str):
    with _disabled_lock:
        _disabled[name] = time.time() + seconds
    logger.warning("search source %s paused for %ds: %s", name, seconds, why)


# ── Text helpers ────────────────────────────────────────────────────────────
def words(text: str) -> List[str]:
    return [w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if w not in _STOP and len(w) > 2]


def keyword_query(claim: str, limit: int = 8) -> str:
    """Short keyword query: search APIs do better with this than a full sentence."""
    seen, out = set(), []
    for w in re.findall(r"[A-Za-z0-9]+", claim):
        lw = w.lower()
        if lw in _STOP or len(lw) < 3 or lw in seen:
            continue
        seen.add(lw)
        out.append(w)
    return " ".join(out[:limit]) or claim[:100]


def overlap(claim_words: set, text: str) -> float:
    if not claim_words:
        return 0.0
    return len(claim_words & set(words(text))) / len(claim_words)


def domain_of(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def _item(url, title, text, source, kind, **extra) -> dict:
    return {"url": url, "title": (title or "").strip(), "text": (text or "").strip(),
            "source": source or domain_of(url), "kind": kind, **extra}


# ── Sources ─────────────────────────────────────────────────────────────────
def _wikipedia(claim: str) -> List[dict]:
    r = _session.get("https://en.wikipedia.org/w/api.php", params={
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": keyword_query(claim), "gsrlimit": 3,
        "prop": "extracts|info", "exintro": 1, "explaintext": 1, "exlimit": 3, "inprop": "url",
    }, timeout=2.5)
    r.raise_for_status()
    pages = sorted(r.json().get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    return [_item(p.get("fullurl", ""), p.get("title"), p.get("extract", "")[:2000], "Wikipedia", "reference")
            for p in pages if p.get("extract")]


def _ddg_text(claim: str) -> List[dict]:
    from ddgs import DDGS
    results = DDGS(timeout=3).text(claim[:200], max_results=6)
    return [_item(r.get("href", ""), r.get("title"), r.get("body"), None, "web") for r in results or []]


def _ddg_news(claim: str) -> List[dict]:
    from ddgs import DDGS
    results = DDGS(timeout=3).news(keyword_query(claim), max_results=5)
    return [_item(r.get("url", ""), r.get("title"), r.get("body"), r.get("source"), "news",
                  published=r.get("date", "")) for r in results or []]


def _gdelt(claim: str) -> List[dict]:
    r = _session.get("https://api.gdeltproject.org/api/v2/doc/doc", params={
        "query": keyword_query(claim, 6), "mode": "artlist", "format": "json",
        "maxrecords": 5, "timespan": "3months", "sort": "hybridrel",
    }, timeout=DEADLINE_S - 0.3)
    if r.status_code != 200 or not r.text.startswith("{"):
        return []
    return [_item(a.get("url", ""), a.get("title"), "", a.get("domain"), "news", published=a.get("seendate", ""))
            for a in r.json().get("articles", [])]


def _tavily(claim: str) -> List[dict]:
    key = os.getenv("TAVILY_API_KEY")
    r = _session.post("https://api.tavily.com/search", json={
        "api_key": key, "query": claim[:300], "max_results": 5, "search_depth": "basic",
    }, timeout=3)
    if r.status_code in (401, 403):
        _disable("tavily", 3600, f"HTTP {r.status_code} (key rejected)")
        return []
    if r.status_code == 429 or r.status_code == 432:
        _disable("tavily", 900, "quota or rate limit")
        return []
    r.raise_for_status()
    return [_item(x.get("url", ""), x.get("title"), x.get("content"), None, "web")
            for x in r.json().get("results", [])]


def _fact_checks(claim: str) -> List[dict]:
    from app.analysis.evidence import _fetch_factcheck_evidence
    out = []
    for a in _fetch_factcheck_evidence(claim):
        text = f'{a.get("source", "")} rated this claim "{a.get("rating", "")}". {a.get("title", "")}'
        out.append(_item(a["url"], a.get("title"), text, a.get("source"), "fact_check",
                         rating=a.get("rating", ""), published=a.get("review_date", "")))
    return out


# Sources that often answer late: used if they arrive in time, never waited for.
_BONUS = {"gdelt"}

SOURCES: Dict[str, Callable[[str], List[dict]]] = {
    "fact_check": _fact_checks,
    "wikipedia": _wikipedia,
    "ddg_text": _ddg_text,
    "ddg_news": _ddg_news,
    "gdelt": _gdelt,
}
if os.getenv("TAVILY_API_KEY"):
    SOURCES["tavily"] = _tavily


# ── Scraping ────────────────────────────────────────────────────────────────
def _scrape(url: str, claim_words: set) -> Optional[str]:
    """Fetch a page (size- and time-capped) and return its most relevant paragraphs."""
    from lxml import html as lxml_html

    start = time.monotonic()
    with requests.get(url, headers={"User-Agent": BROWSER_UA, "Accept": "text/html"},
                      timeout=SCRAPE_TIMEOUT_S, stream=True, allow_redirects=True) as r:
        if r.status_code != 200 or "html" not in r.headers.get("Content-Type", ""):
            return None
        chunks, size = [], 0
        for chunk in r.iter_content(32_768):
            chunks.append(chunk)
            size += len(chunk)
            if size >= SCRAPE_MAX_BYTES or time.monotonic() - start > SCRAPE_TIMEOUT_S:
                break
    doc = lxml_html.fromstring(b"".join(chunks))
    for bad in doc.xpath("//script|//style|//nav|//footer|//header|//aside|//form"):
        bad.drop_tree()
    paras = [re.sub(r"\s+", " ", p.text_content()).strip() for p in doc.xpath("//p|//li")]
    paras = [p for p in paras if len(p) > 60]
    if not paras:
        return None
    best = sorted(paras, key=lambda p: overlap(claim_words, p), reverse=True)[:2]
    if overlap(claim_words, " ".join(best)) < 0.25:
        return None
    return " ".join(best)[:PASSAGE_CHARS * 2]


# ── Orchestration ───────────────────────────────────────────────────────────
def _relevant(claim_words: set, it: dict) -> float:
    return overlap(claim_words, f'{it["title"]} {it["text"]}')


def _rank(found: List[dict], claim_words: set) -> List[dict]:
    """Fact-checks first, then relevance; drop items that don't mention the claim."""
    def score(it):
        return (it["kind"] == "fact_check", _relevant(claim_words, it) + (0.1 if it.get("scraped") else 0))
    ranked = [dict(it, text=it["text"][:PASSAGE_CHARS]) for it in sorted(found, key=score, reverse=True)
              if it["kind"] == "fact_check" or _relevant(claim_words, it) >= 0.2]
    return ranked[:MAX_PASSAGES]


def iter_search(claim: str, deadline_s: float = DEADLINE_S):
    """
    Search every free source in parallel and report progress as it happens.

    Yields ("found", items) each time a source returns new relevant results
    (fact-checks arrive this way in well under a second), and finally
    ("done", passages) with the ranked passages for the verdict model.
    """
    t0 = time.monotonic()
    end = t0 + deadline_s
    claim_words = set(words(claim))

    pending: Dict[Future, str] = {
        _POOL.submit(fn, claim): name for name, fn in SOURCES.items() if _source_on(name)
    }
    found: List[dict] = []
    seen_urls = set()
    scraped = 0
    timings = {}

    while pending:
        remaining = end - time.monotonic()
        if remaining <= 0 or all(name in _BONUS for name in pending.values()):
            break
        if (time.monotonic() - t0 >= ENOUGH_AFTER_S and
                sum(1 for it in found if _relevant(claim_words, it) >= 0.3) >= ENOUGH_PASSAGES):
            break
        # Wake up at ENOUGH_AFTER_S even if nothing new arrived, to re-check "enough".
        until_enough = ENOUGH_AFTER_S - (time.monotonic() - t0)
        timeout = min(remaining, until_enough) if until_enough > 0 else remaining
        done, _ = wait(list(pending), timeout=timeout, return_when=FIRST_COMPLETED)
        for fut in done:
            name = pending.pop(fut)
            timings[name] = round(time.monotonic() - t0, 2)
            try:
                result = fut.result()
            except Exception as e:
                timings[name] = f"err {type(e).__name__}"
                continue
            if name.startswith("scrape:"):
                url = name[7:]
                if result:
                    for it in found:
                        if it["url"] == url:
                            it["text"] = result
                            it["scraped"] = True
                continue
            new = []
            for it in result or []:
                url = it.get("url") or ""
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                found.append(it)
                if it["kind"] == "fact_check" or _relevant(claim_words, it) >= 0.2:
                    new.append(it)
                # Scrape promising web/news pages while other sources are still searching.
                if (scraped < SCRAPE_PAGES and it["kind"] in ("web", "news")
                        and not any(s in url for s in _SKIP_SCRAPE)
                        and _relevant(claim_words, it) >= 0.3
                        and end - time.monotonic() > 0.8):
                    scraped += 1
                    pending[_POOL.submit(_scrape, url, claim_words)] = f"scrape:{url}"
            if new:
                yield "found", new

    for fut in pending:            # past the deadline: stop waiting, never block the request
        fut.cancel()

    ranked = _rank(found, claim_words)
    logger.info("search: %d passages in %.2fs (%s)", len(ranked), time.monotonic() - t0, timings)
    yield "done", ranked


def search_evidence(claim: str, deadline_s: float = DEADLINE_S) -> List[dict]:
    """
    Gather passages for a claim from every free source within `deadline_s`.
    Returns up to MAX_PASSAGES items, published fact-checks first, then by
    relevance. Each item: url, title, text, source, kind (+ rating/published).
    """
    passages: List[dict] = []
    for kind, payload in iter_search(claim, deadline_s):
        if kind == "done":
            passages = payload
    return passages


# ── From passages + model judgement to the app's evidence format ────────────
_CITE = re.compile(r"\[(\d+)\]")


def to_evidence(passages: List[dict], grounded: Optional[dict]):
    """
    Turn passages (and the grounded model's per-source stances) into
    (evidence_score, urls, articles, explanation). Cited sources come first
    and the explanation's [n] markers are renumbered to match that order.
    Published fact-checks keep the stance implied by their own rating.
    """
    from app.analysis.credibility import get_trust_score, get_trust_label
    from app.analysis.evidence import _consistency_score, _rating_stance
    from app.analysis.publisher_bias import get_bias_label

    explanation = (grounded or {}).get("explanation", "")
    stances = (grounded or {}).get("stances", {})

    cited = []
    for m in _CITE.finditer(explanation):
        i = int(m.group(1))
        if 1 <= i <= len(passages) and i not in cited:
            cited.append(i)
    order = cited + [i for i in range(1, len(passages) + 1) if i not in cited]
    new_index = {old: new for new, old in enumerate(order, 1)}
    explanation = _CITE.sub(lambda m: f"[{new_index.get(int(m.group(1)), m.group(1))}]", explanation)

    articles = []
    for old in order:
        p = passages[old - 1]
        model_stance = {"support": "support", "refute": "contradict"}.get(stances.get(old), "neutral")
        stance = _rating_stance(p.get("rating", "")) if p["kind"] == "fact_check" else model_stance
        url = p["url"]
        articles.append({
            "title":       p.get("title", ""),
            "url":         url,
            "source":      p.get("source", ""),
            "snippet":     p.get("text", "")[:300],
            "stance":      stance,
            "rating":      p.get("rating", ""),
            "published":   p.get("published", ""),
            "kind":        p.get("kind", ""),
            "cited":       old in cited,
            "model_stance": model_stance,
            "trust_score": max(get_trust_score(url), 0.85) if p["kind"] == "fact_check" else get_trust_score(url),
            "trust_label": get_trust_label(url),
            "bias_label":  get_bias_label(url),
        })

    judged = [a for a in articles if a["stance"] != "neutral"]
    score = _consistency_score(judged) if judged else None   # nothing judged = unknown
    return score, [a["url"] for a in articles], articles, explanation


def reconcile(verdict: str, confidence: float, articles: List[dict]):
    """
    Keep the verdict consistent with the evidence. Models occasionally answer
    "uncertain" while every source they cite points one way; in that case the
    evidence decides, at moderate confidence. A published fact-check only
    counts when the model itself judged it to be about this claim.
    """
    if verdict != "uncertain":
        return verdict, confidence
    support = [a for a in articles if a.get("model_stance") == "support"]
    refute = [a for a in articles if a.get("model_stance") == "contradict"]
    fc_refutes = any(a.get("kind") == "fact_check" and a.get("stance") == "contradict"
                     and a.get("model_stance") == "contradict" for a in articles)
    fc_supports = any(a.get("kind") == "fact_check" and a.get("stance") == "support"
                      and a.get("model_stance") == "support" for a in articles)
    if not support and (fc_refutes or len(refute) >= 2):
        return "fake", 0.8
    if not refute and (fc_supports or len(support) >= 2):
        return "real", 0.8
    return verdict, confidence
