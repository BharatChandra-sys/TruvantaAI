<!-- Copyright 2027 Bodapati Bharat Chandra. All rights reserved. -->
<!-- Licensed under the Apache License, Version 2.0 | SPDX-License-Identifier: Apache-2.0 -->

<p align="center">
  <img src="docs/assets/hero.svg" alt="Truvanta. Know what's true. Highlight a claim on a web page and Truvanta returns a verdict with its sources." width="100%"/>
</p>

<p align="center">
  <a href="https://truvantaai.tech/install"><b>Install</b></a>
  &nbsp;&middot;&nbsp;
  <a href="https://truvantaai.tech">Website</a>
  &nbsp;&middot;&nbsp;
  <a href="#how-a-check-works">How it works</a>
  &nbsp;&middot;&nbsp;
  <a href="#api">API</a>
  &nbsp;&middot;&nbsp;
  <a href="LICENSE">Apache 2.0</a>
</p>

---

Truvanta is a browser extension that fact-checks what you read, where you read it. Highlight a sentence on any page and a small card opens next to it. Behind it, models trained for this project, a vector memory of past checks with hybrid BM25 and semantic retrieval, and a live search of published fact-checks, news, reference works and research all work on the claim at once. The result is a verdict that cites the sources it actually read. When the evidence doesn't settle the question, it says so.

It is free, open source, and runs on free infrastructure end to end.

## Why it exists

Claims travel faster than corrections. Checking one properly means opening tabs, searching, and reading, which almost nobody does mid-scroll. The obvious shortcut, asking a chatbot, has two problems: it answers from memory, so it knows nothing about recent events, and it sounds just as confident when it is wrong.

Truvanta is built around the opposite rule: **no sources, no verdict.** Every answer is grounded in passages retrieved for that specific claim, every statement points at its source, and missing evidence produces "Uncertain", never a guess.

## How a check works

<p align="center">
  <img src="docs/assets/pipeline.svg" alt="Architecture: claim intake feeds three parallel lanes (own ML models, memory and RAG retrieval, live evidence), which combine in grounded reasoning and a calibrated decision model, producing the live card, a memory write and monitoring." width="100%"/>
</p>

1. **Selection.** Highlight text and press **Check**, right-click and choose *TruthScan with TruvantaAI*, or press `Ctrl+Shift+U`. The card opens beside the selection.
2. **Key terms.** The claim is reduced to the terms that find evidence: codes and acronyms (`R-37M`, `ISRO`), names, numbers and quoted phrases are kept; filler and relationship words are dropped. This step uses no AI. A sentence like *"Yes, India moved forward with acquiring the R-37M (RVV-BD) missile from Russia, known as the "AWACS killer""* becomes `India R-37M RVV-BD Russia "AWACS killer"`.
3. **Search, in parallel.** Six free sources are queried at once under a 3.5 second cap:

   | Source | What it contributes |
   |---|---|
   | Google Fact Check Tools | Ratings published by professional fact-checkers (Snopes, PolitiFact, Full Fact and others) |
   | Google News (local and global editions) | Recent reporting, dated |
   | Bing News | Recent reporting with text snippets |
   | Wikipedia | Background and settled facts |
   | PubMed | Peer-reviewed studies, for health claims only |
   | Web search | General results, treated as low reliability |

   The most promising pages are scraped while other sources are still answering, and only the paragraphs that match the claim are kept. Results are ranked by evidence type (fact-checks, then research, then reference, then news), relevance and independence: at most two items per outlet, and the same story syndicated under several URLs counts once.
4. **Verdict.** A language model reads only those numbered passages, decides whether they support or refute the claim, cites each statement as `[n]`, and marks every source as supporting, refuting or neutral. It is told explicitly that "Uncertain" is a valid answer and that low-reliability results can never decide a verdict on their own.
5. **Card.** Results stream in as they happen: sources appear in about half a second, a matching published fact-check shows as an early answer within about a second, and the final verdict follows in roughly three to five seconds.

### Built not to fail quietly

- **Source health.** A source that fails three times in a row is rested for five minutes, then retried automatically. A source whose key is rejected is paused for an hour.
- **Rescue round.** If fewer than two relevant sources come back, a second, shorter query runs against the fastest sources.
- **Slow sources never hold up a result.** Sources that are often blocked or slow (DuckDuckGo, GDELT) count when they arrive in time; once three relevant sources are in, the search stops waiting for them.
- **Self-healing model selection.** No model names are hard-coded. Each provider's current models are discovered at runtime and ranked by how they actually behave: a model that disappears or needs payment is held for six hours and the provider's list is refreshed; rate limits back off from 30 seconds to 10 minutes; a rejected key pauses that provider. Groq answers first, and other providers are only asked if it is slow.
- **No model, no guess.** If no model is available, a published fact-check can still decide the verdict. Otherwise the answer is "Uncertain".

## Under the hood

Truvanta is more than a search wrapper. Three lanes work on every claim: models trained for this project, a persistent memory of past checks with hybrid retrieval, and live evidence from the web. A grounded reasoning step and a calibrated decision model combine them, and every result feeds back into memory and monitoring.

### Own models

Every claim is scored by classifiers trained for this project. They are tried in order, and each level is used only if the one before it is unavailable, so a score is always produced:

| Level | Model | Accuracy | Notes |
|---|---|---|---|
| 1 | Prediction cache | — | Redis, or an in-process store when Redis is absent |
| 2 | Fine-tuned DeBERTa-v3 (`Bharat2004/deberta-fakenews-detector`) | 96.6% | Trained on 273,932 samples from seven datasets, F1 0.965 |
| 3 | RoBERTa `factcheckai-model-a`, and the a + b ensemble weighted 0.6 / 0.4 | 96.3% (a), 79.8% (b) | Served from Hugging Face Spaces |
| 4 | TF-IDF + logistic regression | 94.2% on ISOT | Local, about 50 ms, no external dependency |

Training used MinHash near-duplicate removal (threshold 0.85), a five-fold TF-IDF noise filter, layer-wise learning-rate decay (0.9), label smoothing (0.1), cosine scheduling with warm-up and FP16. Model-b was trained on GonzaloA/fake_news, WELFake, FEVER and two further corpora. Accuracies come from different held-out splits and are not directly comparable.

These models learn the language of misinformation: sensational phrasing, manipulation and templated text. Their score is one of four signals in the decision model, alongside the grounded verdict, the evidence and the manipulation analysis. Every score is explainable: **SHAP** values and **transformer attention weights** mark which words drove it, and the card's highlights come from them.

### Persistent memory and RAG

Every completed check is written to a knowledge base so that later checks can build on it.

- **Embeddings.** Claims and evidence are encoded as 384-dimensional vectors with `all-MiniLM-L6-v2`, cached for seven days.
- **pgvector.** Two tables in PostgreSQL: `fact_checks` (claim, verdict, confidence, verification status) and `evidence_documents` (source, stance, trust tier), each with its embedding.
- **Hybrid retrieval.** BM25 full-text search finds exact names, numbers and dates; pgvector cosine search finds paraphrases. The two ranked lists are merged with **Reciprocal Rank Fusion**, so documents that both find rise to the top.
- **Reranking.** A cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) scores each candidate directly against the claim and keeps a balanced set of supporting and contradicting evidence.
- **Verification tiers.** Results are stored as `VERIFIED` (confidence at least 0.82 with evidence at least 0.55), `MODEL_ONLY`, `HUMAN_REVIEWED` or `DISPUTED`, with publication and retrieval dates for temporal reasoning.
- **RAG reasoner and citation validator.** A language model reasons over the retrieved context in a structured format (assessment, supporting and contradicting evidence, citations). Each citation is then checked against the source text it points to, and any the source doesn't support are removed.

### Agentic workflow

The full analysis runs as a nine-node LangGraph state machine. Every node reads and writes one shared, typed state:

```
normalize_claim ──┬── run_ml ──────────┐
                  └── retrieve_memory ─┴── retrieve_live ── rag_reason ── detect_conflicts
                                                                               │
                         write_memory ── meta_decide ── analyze_manipulation ◄─┘
                                                        (re-search when evidence is insufficient)
```

The ML and memory branches run in parallel. `detect_conflicts` routes back to live search when the retrieved evidence is too thin to decide, and `write_memory` persists the result with its verification tier. A set of typed agent tools (`search_news`, `retrieve_similar_claims`, `retrieve_evidence`, `get_source_metadata`, `run_ml_analysis`, `analyze_manipulation`) exposes the same capabilities to the workflow.

### Decision engine

A calibrated logistic regression (`CalibratedClassifierCV`), trained on labelled examples, fuses four signals: the model score, the grounded AI verdict, the evidence score and the manipulation score. When the trained model is unavailable, a weighted heuristic takes over: AI 55–65%, evidence 25%, ML 8–12% and manipulation 8%, with the exact split depending on claim length. Clearly conflicting signals return **Uncertain**, a verdict reached by reading sources leads the style classifiers, and a professional fact-checker's debunk overrides everything else.

### Analysis modules

| Area | Module | What it does |
|---|---|---|
| Language | `multilingual.py` | Detects the language (langdetect) and translates before analysis; XLM-RoBERTa for multilingual classification |
| | `claim_extractor.py` | Splits long text into atomic, checkable claims |
| | `domain_classifier.py` | Tags the claim as medical, climate, political, science and so on, for domain-specific context |
| Signals | `manipulation.py` | Sensational and clickbait language, emotional amplification, absolutes, urgency and fear triggers, unverified attribution |
| | `wikidata.py` | Named-entity recognition (`dslim/bert-large-NER`) and entity verification against Wikidata |
| | `image_check.py` | Checks whether an attached image matches the claim (Gemini Vision) |
| | `audio_transcription.py` | Voice input via Whisper, with Google Speech-to-Text and AssemblyAI as alternatives |
| | `cloud_models.py` | CLIP image-text similarity, adversarial-input detection and "inoculation" explanations of the manipulation technique used |
| Sources | `credibility.py` | Source trust that learns from stance consistency and user corrections |
| | `publisher_bias.py` | Bias ratings for 100+ outlets (AllSides and Media Bias/Fact Check data), used to weight evidence |
| | `platform_tracker.py` | Finds the same claim spreading across platforms and previous debunks |
| Spread | `velocity.py` | Claim frequency in 5-minute, 1-hour and 24-hour windows to flag viral and trending claims |
| | `semantic_clustering.py` | Groups paraphrased variants of the same claim to surface coordinated campaigns |
| | `social_graph.py` | Retweet and cross-post networks on X and Reddit to detect coordinated inauthentic behaviour |
| | `cooldown.py` | Friction score for risky claims: fake probability 40%, velocity 30%, emotional intensity 15%, evidence conflict 15% |
| Explain | `explainability.py` | A signal-by-signal breakdown of why a verdict was reached |
| | `highlight.py`, `shap_explainer.py`, `attention_extractor.py` | Token-level importance from SHAP, attention weights and TF-IDF features |
| Learning | `continuous_learning.py` | Retrains automatically after 50 user corrections, or weekly once 10 have accumulated |
| | `news_aggregator.py` | Collects auto-labelled training data from trusted outlets every hour |
| | `drift.py` | Watches the rolling distribution of verdicts and confidence and alerts on shifts |
| | `ab_testing.py` | Assigns model variants and tracks their outcomes |

Optional integrations such as the social graph (`SOCIAL_GRAPH_ENABLED`) and Wikidata entity checks (`WIKIDATA_ENABLED`) are switched on with environment variables.

## What a verdict means

| Verdict | Meaning |
|---|---|
| **True** | The sources found support the claim. |
| **False** | The sources found refute it, or a professional fact-checker rated a matching claim false. |
| **Uncertain** | The evidence is mixed, doesn't address the claim, or wasn't found. Treat this as "not settled", not as "probably false". |

The confidence figure reflects how clearly the evidence points one way, not a statistical guarantee. Results from low-reliability sources are labelled `low trust` in the card. Each source row links to the original, and its number matches the `[n]` citations in the summary.

## Features

- **In-page card** on any site, with live progress, numbered citations and a follow-up chat that keeps the claim and its evidence as context.
- **Popup** with a full chat, history of past checks (reopened chats keep their fact-check cards), saved claims, a dashboard and settings.
- **Keyboard shortcuts:** `Ctrl+Shift+U` checks the selection, `Ctrl+Shift+L` checks the visible page, `Ctrl+Shift+Y` opens the popup.
- **Accounts** with email or Google sign-in. Checks require signing in; the card prompts for it and resumes the check automatically afterwards.
- **Caching.** Repeat checks return instantly, with Redis when available and an in-memory cache otherwise.
- **Multilingual input.** Claims in other languages are normalized before searching.

## Performance

Measured on the local backend in October 2026, with a fresh cache:

| Stage | Typical time |
|---|---|
| First source in the card | ~0.5 s |
| Published fact-check match (early answer) | ~1 s |
| Search and scraping, all sources | 0.4 – 2.7 s |
| Grounded verdict from the model | ~1 – 2 s |
| Full verdict in the card | 3 – 5 s |
| Repeat check (cached) | instant |

On Render's free tier the backend sleeps after 15 minutes without traffic, so the first check after a quiet period can take 30 to 60 seconds while it wakes. The extension sends a warm-up request as soon as you select text, which hides part of that delay.

## Limitations

- **Coverage depends on what has been published.** Very recent, very local or very specific claims may have no sources yet; those correctly come back "Uncertain".
- **Free sources have limits.** News feeds return headlines and snippets rather than full articles, and some sites block scraping.
- **Not every highlight is a claim.** Song titles, headings and opinions can't be fact-checked; they tend to come back "Uncertain".
- **The model can misread a source.** Every verdict links its evidence so you can check it yourself, and that is the point.

## Install

The extension is installed from the website for now, not the Chrome Web Store.

1. Download the latest ZIP from the [install page](https://truvantaai.tech/install) and extract it to a folder you will keep.
2. Open `chrome://extensions` (or `edge://extensions`) and turn on **Developer mode**.
3. Click **Load unpacked** and choose the extracted folder, the one that contains `manifest.json`.
4. Pin Truvanta from the puzzle-piece menu, sign in, and highlight something to check.

Works in Chrome, Edge, Brave and other Chromium browsers.

## Architecture

```
Browser                                  Backend (FastAPI, Python 3.11)
───────                                  ─────────────────────────────
content.js   in-page toolbar and card    routes/stream_routes.py   POST /check/stream (SSE)
   │  port: "truvanta-check"             analysis/search.py        parallel search, scraping, ranking
   ▼                                     analysis/ai.py            grounded verdict, hedged providers
service_worker.js                        analysis/model_registry   self-healing model selection
   │  fetch /check/stream, relay events  analysis/ai_config.py     runtime model discovery
   ▼                                     api.py                    POST /message (popup chat, full pipeline)
Render ───────────────────────────────►  routes/history_routes.py  sessions and messages
                                         cache.py                  Redis or in-memory cache
popup/       chat, history, dashboard    Neon PostgreSQL           users, history, pgvector memory
```

The in-page card never calls the backend directly: requests from a content script carry the website's origin, which the backend's CORS policy rejects. The background worker makes the request and relays each streamed event to the card over a long-lived port; closing the card cancels the request.

| Component | Technology | Hosted on |
|---|---|---|
| Extension | Manifest V3, vanilla JavaScript, Shadow DOM for the in-page UI | The user's browser |
| API | FastAPI, Python 3.11 | Render (free) |
| Database | PostgreSQL with pgvector | Neon (free) |
| Own models | Fine-tuned DeBERTa-v3, RoBERTa ensemble, TF-IDF fallback | Hugging Face Spaces (free) and in-process |
| Memory and retrieval | all-MiniLM-L6-v2 embeddings, pgvector, BM25, RRF, ms-marco cross-encoder | Neon and in-process |
| Orchestration | LangGraph state machine with typed agent tools | In-process |
| Language models | Groq, Gemini, OpenRouter free tiers, discovered at runtime | External APIs |
| Evidence | Google Fact Check, Google News, Bing News and web, Wikipedia, PubMed, DuckDuckGo, GDELT | External APIs and feeds |
| Website | Next.js | Vercel |

```
TruvantaAI/
├── backend/
│   ├── app/
│   │   ├── analysis/      search.py, ai.py, ai_config.py, model_registry.py, evidence.py, ...
│   │   ├── routes/        stream_routes.py, history_routes.py, auth_routes.py, ...
│   │   ├── rag/           reasoner.py, citation_validator.py
│   │   ├── retrieval/     embeddings.py, vector_store.py, hybrid.py (BM25 + vector + RRF), reranker.py
│   │   ├── agents/        tools.py, typed tools for the agentic workflow
│   │   ├── graph/         LangGraph workflow: nine nodes from normalization to memory write
│   │   ├── logic/         decision.py, the multi-signal decision model used by /message
│   │   ├── api.py         POST /message
│   │   └── main.py        app startup, middleware, scheduler
│   ├── alembic/           database migrations
│   └── tests/
├── extension/
│   ├── content.js         in-page toolbar and card
│   ├── env.js             which backend the extension talks to
│   ├── background/        service worker: messaging, streaming relay, shortcuts, context menu
│   └── popup/             chat, history, dashboard, saved, settings
├── factcheckai-website/   Next.js site with the install page and extension downloads
├── ml-servers/            Hugging Face Space for the classifier ensemble
└── docs/                  research notes, product plan, README assets
```

## Running locally

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
cp .env.example .env              # then fill in the keys below
uvicorn app.main:app --reload --port 8000
```

Useful environment variables (names only; never commit the values):

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string. Point it at a development database, not production, when testing locally. |
| `JWT_SECRET` | Signing key for login tokens (`openssl rand -hex 32`) |
| `GOOGLE_CLIENT_ID` | Google sign-in |
| `GOOGLE_FACTCHECK_API_KEY` | Published fact-checks (free Google Cloud key, no billing needed) |
| `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY` | Language model providers; any one is enough |
| `TAVILY_API_KEY` | Optional extra web search (free monthly quota) |
| `NEWS_REGION`, `NEWS_LANG`, `NEWS_CEID` | Google News edition, default India (`IN`, `en-IN`, `IN:en`) |
| `REDIS_ENABLED`, `REDIS_URL` | Optional shared cache and per-user rate limits |
| `BREVO_API_KEY`, `SMTP_USER` | Password-reset email |

### Extension

1. In `extension/env.js`, set `USE_LOCAL_BACKEND = true` to use `http://127.0.0.1:8000`. Set it back to `false` before building a release.
2. Load the `extension` folder with **Load unpacked**, as in the install steps.
3. After editing extension files, reload it at `chrome://extensions` and refresh open tabs.

### Tests

```bash
cd backend
python -m pytest tests -q
```

## API

All check endpoints require a bearer token.

**Sign up or log in**

```bash
curl -X POST https://factcheckai-coq3.onrender.com/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"...","name":"Your Name"}'
# {"token": "eyJ...", "user": {...}}
```

**Real-time check (Server-Sent Events)**

```bash
curl -N -X POST https://factcheckai-coq3.onrender.com/check/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"The Great Wall of China is visible from the Moon"}'
```

```
event: start      data: {"claim": "..."}
event: sources    data: {"items": [{"url", "title", "source", "kind", "rating"}]}
event: factcheck  data: {"source": "Snopes", "rating": "False", "stance": "contradict", ...}
event: judging    data: {"count": 6}
event: verdict    data: {"verdict": "fake", "confidence": 0.96, "explanation": "... [1][2]",
                         "evidence_articles": [...], "evidence_score": 0.0, "grounded": true}
event: done       data: {"ms": 3480}
```

`sources` can arrive several times. `verdict` is `real`, `fake` or `uncertain`; each item in `evidence_articles` carries `stance`, `cited`, `kind`, `rating`, `published` and `low_trust`.

**Full pipeline and chat** (used by the popup)

```bash
curl -X POST https://factcheckai-coq3.onrender.com/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"...", "check": true}'
```

`check: true` skips the chat-or-claim classification step. The response adds the classifier, manipulation and explainability signals to the verdict.

**Other endpoints:** `GET /health`, `GET /history/sessions`, `GET /history/sessions/{id}/messages`.

## Roadmap

- Local index of published fact-checks (ClaimReview) for instant matches with no API call
- Small CPU-only models for stance detection and citation checking, to depend less on hosted language models
- Detecting text that isn't a factual claim (titles, headings, opinions) before searching
- An always-on host to remove cold starts
- An evaluation set with published accuracy, calibration and latency numbers
- Chrome Web Store and Firefox releases

The longer-term direction is in the [3.0 product plan](docs/PRODUCT_PLAN.md).

## Contributing

Issues and pull requests are welcome. Please branch from `main`, use conventional commit prefixes (`feat:`, `fix:`, `docs:`), and describe what you tested. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security

Passwords are hashed and login tokens are signed JWTs. Input is validated and sanitized, database access goes through the ORM, and API keys stay on the server. To report a vulnerability, see [SECURITY.md](SECURITY.md).

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

Training data: LIAR (Wang, 2017), ISOT Fake News, FakeNewsNet (Shu et al., 2018), daniB2112/fake-news-dataset, WELFake, GonzaloA/fake_news and FEVER v1.0.

```bibtex
@software{truvanta2026,
  title   = {Truvanta: Source-Grounded Fact-Checking in the Browser},
  author  = {Bodapati Bharat Chandra},
  year    = {2026},
  url     = {https://github.com/BharatChandra-sys/TruvantaAI},
  version = {2.6.3},
  license = {Apache-2.0}
}
```
