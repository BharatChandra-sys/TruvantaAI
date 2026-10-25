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
MIN_RELEVANCE = 0.3         # share of the claim's weighted key terms a source must cover
PASSAGE_CHARS = 600

USER_AGENT = "TruvantaFactCheck/2.6 (+https://github.com/BharatChandra-sys/TruvantaAI)"
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/141.0 Safari/537.36")

# Shared pool: search and scrape tasks of concurrent requests interleave here.
_POOL = ThreadPoolExecutor(max_workers=16, thread_name_prefix="search")
_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT})

# Sites whose pages add nothing as evidence or block scrapers.
_SKIP_SCRAPE = ("news.google.com", "youtube.com", "tiktok.com", "facebook.com", "instagram.com", "x.com",
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


# Words that carry no search value in a claim ("Yes, India moved forward with...").
_FILLER = {
    "yes", "no", "moved", "forward", "widely", "known", "called", "dubbed", "reportedly",
    "according", "said", "says", "say", "claims", "claim", "claimed", "report", "reports",
    "reported", "news", "now", "today", "recently", "officially", "finally", "really",
    "actually", "like", "per", "via", "amid", "while", "since", "still", "even", "going",
    "get", "got", "make", "made", "many", "much", "some", "any", "all", "one", "two",
    "every", "your", "our", "my", "their", "its", "people", "thing", "things",
}
# Relationship words say how things relate; the things themselves find sources.
_RELATION = {
    "lower", "lowers", "raise", "raises", "cause", "causes", "caused", "increase", "increases",
    "reduce", "reduces", "prevent", "prevents", "boost", "boosts", "cut", "cuts", "help", "helps",
    "make", "makes", "show", "shows", "become", "becomes", "lead", "leads", "kill", "kills",
}
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-.]*[A-Za-z0-9]|[A-Za-z0-9]")
_QUOTED = re.compile(r'"([^"]{3,60})"|“([^”]{3,60})”')


def _norm(word: str) -> str:
    """Loose form for matching: case, hyphens and simple word endings ignored."""
    w = word.lower().replace("-", "").replace(".", "")
    if w.isalpha() and len(w) > 6:
        return w[:6]                       # missiles/missile, russian/russia
    if w.isalpha() and len(w) > 3:
        return w.rstrip("s")
    return w


def key_terms(claim: str) -> List[tuple]:
    """
    The claim's search terms in their original order, each with a weight:
    3 for quoted phrases, codes and acronyms (R-37M, AWACS, 2023),
    2 for names (India, Russia), 1 for other content words; filler dropped.
    """
    terms, seen = [], set()
    for m in _QUOTED.finditer(claim):
        phrase = (m.group(1) or m.group(2)).strip()
        terms.append((m.start(), phrase, 3, True))
        seen.update(_norm(t) for t in _TOKEN.findall(phrase))
    for m in _TOKEN.finditer(claim):
        tok = m.group(0)
        low = tok.lower()
        has_digit = any(c.isdigit() for c in tok)
        if (low in _STOP or low in _FILLER or (len(low) < 2 and not has_digit)
                or _norm(tok) in seen):
            continue
        seen.add(_norm(tok))
        sentence_start = not claim[:m.start()].strip() or claim[:m.start()].rstrip()[-1] in ".!?:"
        wordy = low in _RELATION or re.search(r"(ing|ed|ly)$", low) is not None
        if has_digit or (tok.isupper() and len(tok) >= 2) or                 ("-" in tok and any(c.isupper() for c in tok[1:])):
            weight = 3
        elif tok[0].isupper() and not (sentence_start and wordy):
            weight = 2
        elif wordy:
            weight = 0.5
        elif len(low) > 2:
            weight = 1
        else:
            continue
        terms.append((m.start(), tok, weight, False))
    terms.sort()
    return [(t, w, phrase) for _, t, w, phrase in terms]


def keyword_query(claim: str, limit: int = 6) -> str:
    """Short query of the claim's strongest terms, in their original order."""
    terms = key_terms(claim)
    if not terms:
        return claim[:100]
    # Strongest first; among equals, longer (more specific) words win.
    strongest = set(sorted(range(len(terms)), key=lambda i: (-terms[i][1], -len(terms[i][0])))[:limit])
    return " ".join(f'"{t}"' if phrase else t for i, (t, _w, phrase) in enumerate(terms) if i in strongest)


class Relevance:
    """How much of a claim's important content a text covers (0-1), weighted by key_terms."""

    def __init__(self, claim: str, top: int = 8):
        terms = sorted(key_terms(claim), key=lambda t: (-t[1], -len(t[0])))[:top]
        self.terms = [(t.lower(), {_norm(x) for x in _TOKEN.findall(t)}, w, phrase) for t, w, phrase in terms]
        self.total = sum(w for _, _, w, _ in self.terms) or 1

    def __call__(self, text: str) -> float:
        low = (text or "").lower()
        forms = {_norm(t) for t in _TOKEN.findall(text or "")}
        forms |= {_norm(p) for t in _TOKEN.findall(text or "") for p in t.split("-") if p}
        got = 0.0
        for raw, parts, weight, phrase in self.terms:
            if phrase:
                if raw in low:
                    got += weight
                elif parts:
                    got += weight * 0.5 * len(parts & forms) / len(parts)
            elif parts & forms:
                got += weight
        return got / self.total


def overlap(claim_words, text: str) -> float:
    """Relevance of `text` to a claim; `claim_words` is a Relevance instance."""
    return claim_words(text)


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
        "gsrsearch": keyword_query(claim, 4).replace('"', ""), "gsrlimit": 3,
        "prop": "extracts|info", "exintro": 1, "explaintext": 1, "exlimit": 3, "inprop": "url",
    }, timeout=2.5)
    r.raise_for_status()
    pages = sorted(r.json().get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99))
    return [_item(p.get("fullurl", ""), p.get("title"), p.get("extract", "")[:2000], "Wikipedia", "reference")
            for p in pages if p.get("extract")]


def _ddg_text(claim: str) -> List[dict]:
    from ddgs import DDGS
    results = DDGS(timeout=3).text(keyword_query(claim, 7), max_results=8)
    return [_item(r.get("href", ""), r.get("title"), r.get("body"), None, "web") for r in results or []]


def _ddg_news(claim: str) -> List[dict]:
    from ddgs import DDGS
    results = DDGS(timeout=3).news(keyword_query(claim, 6), max_results=6)
    return [_item(r.get("url", ""), r.get("title"), r.get("body"), r.get("source"), "news",
                  published=r.get("date", "")) for r in results or []]


def _rss_items(url: str, params: dict, timeout: float = 3) -> list:
    from xml.etree import ElementTree as ET
    r = _session.get(url, params=params, headers={"User-Agent": BROWSER_UA}, timeout=timeout)
    r.raise_for_status()
    return ET.fromstring(r.content).findall(".//item")


def _rss_date(text: str) -> str:
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(text or "").date().isoformat()
    except (TypeError, ValueError):
        return ""


def _google_news_feed(claim: str, lang: str, region: str, ceid: str) -> List[dict]:
    out = []
    for it in _rss_items("https://news.google.com/rss/search", {
        "q": keyword_query(claim, 6), "hl": lang, "gl": region, "ceid": ceid,
    })[:8]:
        source_el = it.find("source")
        source = source_el.text if source_el is not None else ""
        title = it.findtext("title") or ""
        if source and title.endswith(f" - {source}"):
            title = title[: -len(source) - 3]
        published = _rss_date(it.findtext("pubDate"))
        out.append(_item(it.findtext("link") or "", title, f"{title}. Reported by {source} on {published}.",
                         source, "news", published=published))
    return out


def _google_news(claim: str) -> List[dict]:
    """Google News, local edition (NEWS_REGION, default India): strong on recent events."""
    return _google_news_feed(claim, os.getenv("NEWS_LANG", "en-IN"), os.getenv("NEWS_REGION", "IN"),
                             os.getenv("NEWS_CEID", "IN:en"))


def _google_news_global(claim: str) -> List[dict]:
    """Google News, international edition: wider coverage than the local one."""
    return _google_news_feed(claim, "en-US", "US", "US:en")


def _bing_news(claim: str) -> List[dict]:
    """Bing News feed: free, no key, and unlike Google News it includes a text snippet."""
    out = []
    for it in _rss_items("https://www.bing.com/news/search", {
        "q": keyword_query(claim, 6), "format": "rss", "setlang": "en-US", "mkt": "en-US",
    })[:8]:
        link = it.findtext("link") or ""
        # Bing wraps article links in a redirect; the real URL is in its `url` parameter.
        try:
            from urllib.parse import parse_qs
            link = parse_qs(urlparse(link).query).get("url", [link])[0]
        except Exception:
            pass
        # <News:Source> uses a per-query namespace, so match on the local tag name.
        source = next((c.text for c in it if c.tag.endswith("}Source") and c.text), "") or domain_of(link)
        desc = re.sub(r"<[^>]+>", "", it.findtext("description") or "")
        out.append(_item(link, it.findtext("title"), desc, source, "news",
                         published=_rss_date(it.findtext("pubDate"))))
    return out


# Bing's web feed is fast and free but noisy (it can return unrelated or spam
# pages), so its results are kept only when clearly on topic and weighted low.
_SPAM = re.compile(r"porn|xxx|xhamster|sex|nude|casino|betting|escort|onlyfans|hentai|torrent|crack",
                   re.IGNORECASE)
LOW_TRUST_MIN_RELEVANCE = 0.7   # must cover nearly all of the claim's key terms


def _bing_web(claim: str) -> List[dict]:
    """Bing web results (free, no key). Low reliability: tagged so every step weighs them down."""
    out = []
    for it in _rss_items("https://www.bing.com/search", {
        "q": keyword_query(claim, 6), "format": "rss", "adlt": "strict",
        "setlang": "en-US", "cc": "US", "mkt": "en-US",
    })[:8]:
        link = it.findtext("link") or ""
        title = it.findtext("title") or ""
        if not link.startswith("http") or _SPAM.search(link) or _SPAM.search(title):
            continue
        out.append(_item(link, title, re.sub(r"<[^>]+>", "", it.findtext("description") or ""),
                         None, "web", low_trust=True))
    return out


_HEALTH = re.compile(
    r"\b(vaccin\w*|cancer|covid\w*|virus|viral|disease|cure[sd]?|drug|medicine|medical|health|diet|"
    r"vitamin\w*|autism|diabet\w*|heart|blood|doctor\w*|treatment|symptom\w*|pandemic|infection|"
    r"study|studies|clinical|immun\w*|obesity|nutrition|protein|sugar|alcohol|smoking|pregnan\w*)\b",
    re.IGNORECASE,
)


def _pubmed(claim: str) -> List[dict]:
    """Peer-reviewed research from PubMed (free, no key). Only for health claims."""
    if not _HEALTH.search(claim):
        return []
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    ids = _session.get(f"{base}/esearch.fcgi", params={
        "db": "pubmed", "term": keyword_query(claim, 5).replace('"', ""), "retmax": 4,
        "retmode": "json", "sort": "relevance", "tool": "truvanta",
    }, timeout=2.5).json().get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    docs = _session.get(f"{base}/esummary.fcgi", params={
        "db": "pubmed", "id": ",".join(ids), "retmode": "json", "tool": "truvanta",
    }, timeout=2.5).json().get("result", {})
    out = []
    for i in ids:
        d = docs.get(i) or {}
        title = d.get("title", "")
        journal, year = d.get("source", ""), (d.get("pubdate") or "")[:4]
        out.append(_item(f"https://pubmed.ncbi.nlm.nih.gov/{i}/", title,
                         f"{title} Peer-reviewed study in {journal} ({year}).", journal or "PubMed",
                         "research", published=year))
    return out


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
    # Long sentences find few fact-checks; their key terms find more.
    query = claim if len(claim) <= 120 else keyword_query(claim, 6).replace('"', "")
    for a in _fetch_factcheck_evidence(query):
        text = f'{a.get("source", "")} rated this claim "{a.get("rating", "")}". {a.get("title", "")}'
        out.append(_item(a["url"], a.get("title"), text, a.get("source"), "fact_check",
                         rating=a.get("rating", ""), published=a.get("review_date", "")))
    return out


# Slow or often-blocked sources: their results count if they arrive in time, but
# once BONUS_ENOUGH relevant sources are in, the search stops waiting for them.
_BONUS = {"gdelt", "ddg_text", "ddg_news"}
BONUS_ENOUGH = 3

SOURCES: Dict[str, Callable[[str], List[dict]]] = {
    "fact_check": _fact_checks,
    "wikipedia": _wikipedia,
    "google_news": _google_news,
    "google_news_global": _google_news_global,
    "bing_news": _bing_news,
    "pubmed": _pubmed,
    "bing_web": _bing_web,
    "ddg_text": _ddg_text,
    "ddg_news": _ddg_news,
    "gdelt": _gdelt,
}
if os.getenv("TAVILY_API_KEY"):
    SOURCES["tavily"] = _tavily

# Second, shorter-query round when the first finds too little. Fast sources only.
RESCUE_SOURCES = ("google_news_global", "google_news", "bing_news", "wikipedia", "fact_check")
RESCUE_DEADLINE_S = 2.0
RESCUE_BELOW = 2            # run the rescue round when fewer relevant sources than this

# ── Circuit breaker: a source that keeps failing is rested, then retried ───
_FAILS_BEFORE_REST = 3
_REST_S = 300
_fail_counts: Dict[str, int] = {}


def _record(name: str, ok: bool, why: str = ""):
    with _disabled_lock:
        _fail_counts[name] = 0 if ok else _fail_counts.get(name, 0) + 1
        tripped = not ok and _fail_counts[name] >= _FAILS_BEFORE_REST
        if tripped:
            _fail_counts[name] = 0
    if tripped:
        _disable(name, _REST_S, f"{_FAILS_BEFORE_REST} failures in a row ({why})")


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
def _relevant(claim_words, it: dict) -> float:
    return overlap(claim_words, f'{it["title"]} {it["text"]}')


def _keep(claim_words, it: dict) -> bool:
    """Whether a result is relevant enough to use; low-reliability results need more."""
    if it["kind"] == "fact_check":
        return True
    bar = LOW_TRUST_MIN_RELEVANCE if it.get("low_trust") else MIN_RELEVANCE
    return _relevant(claim_words, it) >= bar


# Stronger kinds of evidence rank above general news at similar relevance.
_KIND_BOOST = {"fact_check": 1.0, "research": 0.15, "reference": 0.05}
MAX_PER_SOURCE = 2          # independent outlets beat many articles from one


def _rank(found: List[dict], claim_words) -> List[dict]:
    """Fact-checks first, then stronger evidence and relevance, at most MAX_PER_SOURCE per outlet."""
    def score(it):
        return (_relevant(claim_words, it) + _KIND_BOOST.get(it["kind"], 0)
                + (0.1 if it.get("scraped") else 0) - (0.15 if it.get("low_trust") else 0))
    ranked, per_source, titles = [], {}, set()
    for it in sorted(found, key=score, reverse=True):
        if not _keep(claim_words, it):
            continue
        # The same story syndicated under several URLs counts once.
        title_key = re.sub(r"\W+", " ", it.get("title", "").lower()).strip()[:80]
        if title_key and title_key in titles:
            continue
        titles.add(title_key)
        outlet = (it.get("source") or domain_of(it["url"])).lower()
        if per_source.get(outlet, 0) >= MAX_PER_SOURCE:
            continue
        per_source[outlet] = per_source.get(outlet, 0) + 1
        ranked.append(dict(it, text=it["text"][:PASSAGE_CHARS]))
    return ranked[:MAX_PASSAGES]


def _wave(query: str, names, end: float, t0: float, rel, state: dict, timings: dict, label: str):
    """
    Run `names` sources for `query` in parallel until `end`, scraping promising
    pages on the way. Yields lists of newly found relevant items. Updates
    state["found"], state["seen"], state["scraped"].
    """
    pending: Dict[Future, str] = {
        _POOL.submit(SOURCES[n], query): n for n in names if n in SOURCES and _source_on(n)
    }
    found = state["found"]
    while pending:
        remaining = end - time.monotonic()
        if remaining <= 0:
            break
        if all(name in _BONUS for name in pending.values()) and sum(
                1 for it in found if _keep(rel, it) and not it.get("low_trust")) >= BONUS_ENOUGH:
            break
        if (time.monotonic() - t0 >= ENOUGH_AFTER_S and
                sum(1 for it in found if _relevant(rel, it) >= 0.4) >= ENOUGH_PASSAGES):
            break
        # Wake up at ENOUGH_AFTER_S even if nothing new arrived, to re-check "enough".
        until_enough = ENOUGH_AFTER_S - (time.monotonic() - t0)
        timeout = min(remaining, until_enough) if until_enough > 0 else remaining
        done, _ = wait(list(pending), timeout=timeout, return_when=FIRST_COMPLETED)
        for fut in done:
            name = pending.pop(fut)
            key = name if name.startswith("scrape:") else f"{label}{name}"
            timings[key] = round(time.monotonic() - t0, 2)
            try:
                result = fut.result()
            except Exception as e:
                timings[key] = f"err {type(e).__name__}"
                if not name.startswith("scrape:"):
                    _record(name, False, type(e).__name__)
                continue
            if name.startswith("scrape:"):
                url = name[7:]
                if result:
                    for it in found:
                        if it["url"] == url:
                            it["text"] = result
                            it["scraped"] = True
                continue
            _record(name, True)
            new = []
            for it in result or []:
                url = it.get("url") or ""
                if not url or url in state["seen"]:
                    continue
                state["seen"].add(url)
                found.append(it)
                if _keep(rel, it):
                    new.append(it)
                # Scrape promising web/news pages while other sources are still searching.
                if (state["scraped"] < SCRAPE_PAGES and it["kind"] in ("web", "news")
                        and not any(s in url for s in _SKIP_SCRAPE)
                        and _relevant(rel, it) >= 0.3
                        and end - time.monotonic() > 0.8):
                    state["scraped"] += 1
                    pending[_POOL.submit(_scrape, url, rel)] = f"scrape:{url}"
            if new:
                yield new

    for fut, name in pending.items():   # past the deadline: stop waiting, never block the request
        fut.cancel()
        if not name.startswith("scrape:") and name not in _BONUS:
            _record(name, False, "too slow")


def iter_search(claim: str, deadline_s: float = DEADLINE_S):
    """
    Search every free source in parallel and report progress as it happens.

    Yields ("found", items) each time a source returns new relevant results
    (fact-checks arrive this way in well under a second), and finally
    ("done", passages) with the ranked passages for the verdict model.

    If the first round finds fewer than RESCUE_BELOW relevant sources, a
    second round retries the fastest sources with a shorter query.
    """
    t0 = time.monotonic()
    rel = Relevance(claim)
    state = {"found": [], "seen": set(), "scraped": 0}
    timings: Dict[str, object] = {}

    for new in _wave(claim, list(SOURCES), t0 + deadline_s, t0, rel, state, timings, ""):
        yield "found", new

    relevant = sum(1 for it in state["found"] if _keep(rel, it) and not it.get("low_trust"))
    if relevant < RESCUE_BELOW:
        short = keyword_query(claim, 3).replace('"', "")
        if short and short.lower() != keyword_query(claim, 6).replace('"', "").lower():
            for new in _wave(short, RESCUE_SOURCES, time.monotonic() + RESCUE_DEADLINE_S, t0, rel,
                             state, timings, "rescue:"):
                yield "found", new

    ranked = _rank(state["found"], rel)
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
            "trust_score": (max(get_trust_score(url), 0.85) if p["kind"] == "fact_check"
                            else min(get_trust_score(url), 0.3) if p.get("low_trust")
                            else get_trust_score(url)),
            "low_trust":   bool(p.get("low_trust")),
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
    # Low-reliability results can't settle a verdict on their own.
    support = [a for a in articles if a.get("model_stance") == "support" and not a.get("low_trust")]
    refute = [a for a in articles if a.get("model_stance") == "contradict" and not a.get("low_trust")]
    fc_refutes = any(a.get("kind") == "fact_check" and a.get("stance") == "contradict"
                     and a.get("model_stance") == "contradict" for a in articles)
    fc_supports = any(a.get("kind") == "fact_check" and a.get("stance") == "support"
                      and a.get("model_stance") == "support" for a in articles)
    if not support and (fc_refutes or len(refute) >= 2):
        return "fake", 0.8
    if not refute and (fc_supports or len(support) >= 2):
        return "real", 0.8
    return verdict, confidence


def verdict_without_model(passages: List[dict], articles: List[dict]):
    """
    A verdict when no language model judged the evidence. Never guesses from
    memory: a published fact-check can decide it, otherwise it stays uncertain.
    Returns (verdict, confidence, explanation).
    """
    if not passages:
        return ("uncertain", 0.5,
                "We couldn't find reliable sources about this claim yet. It may be very recent, "
                "very specific, or worded unusually. Try selecting a shorter sentence that states "
                "one fact.")
    checks = [a for a in articles if a.get("kind") == "fact_check"]
    refuted = [a for a in checks if a.get("stance") == "contradict"]
    supported = [a for a in checks if a.get("stance") == "support"]
    if refuted and not supported:
        a = refuted[0]
        return ("fake", 0.75,
                f'{a.get("source") or "A fact-checker"} rated a matching claim "{a.get("rating")}" [1].')
    if supported and not refuted:
        a = supported[0]
        return ("real", 0.75,
                f'{a.get("source") or "A fact-checker"} rated a matching claim "{a.get("rating")}" [1].')
    return ("uncertain", 0.5,
            f"We found {len(passages)} related source{'s' if len(passages) != 1 else ''} but couldn't "
            "weigh them right now. Open them below to judge for yourself.")
