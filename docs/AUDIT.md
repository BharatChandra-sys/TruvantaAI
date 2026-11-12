# Audit: optimizations and improvements at $0/month

Date: 2026-11-12. Scope: `backend/app`, `extension/`, deploy config, repo hygiene.
Nothing was changed. Nothing here was measured on the live server; timings are read from the code.

**Not audited:** the website's React code, `ml-servers/`, `gemini-proxy/` internals, the training scripts, and most of `popup.js` beyond its API calls.

**Clean results:** a pattern scan of tracked files found no API keys or DB passwords. `backend/.env` and `extension_private_key.pem` are git-ignored. `/health/ping` does not query the database, so uptime pings don't keep Neon awake. Google access tokens are checked against our client ID (`auth.py:272-278`).

Impact: H/M/L. Effort: S (under 1 hour), M (half a day), L (more).

## Findings

| # | Area | Finding | File:line | Impact | Effort | Free? |
|---|---|---|---|---|---|---|
| 1 | Speed/RAM | `/message` reloads `model.joblib` and `vectorizer.joblib` from disk on every "fake" or manipulative result, although `_load_tfidf` already holds them in memory | `backend/app/api.py:551-552` | H | S | yes |
| 2 | Quota/Security | `/message` works without sign-in, so anyone can spend the LLM and search quota. `/upload`, `/audio/*` and `/explain` are the same. The popup already forces login | `api.py:245`, `routes/upload_routes.py:140`, `routes/audio_routes.py:29,147`, `routes/explain_routes.py:60`, `extension/popup/popup.js:13` | H | S | yes |
| 3 | Quota | `/check/stream` has no entry in the rate-limit table, so it gets the default 60/min per IP. Each uncached check can make 2 LLM calls plus about 8 searches | `backend/app/middleware.py:20-31`, `routes/stream_routes.py:186,237` | H | S | yes |
| 4 | Quota | `fresh: true` is accepted from any client and skips the cache and memory. It was meant for the evaluation only | `backend/app/schemas.py:30`, `stream_routes.py:146,163` | M | S | yes |
| 5 | Speed/Quota | `/message` never reads the stream cache or the pgvector memory. A claim the card just settled is searched and judged again when the user opens the full report | `api.py:134-136`, `stream_routes.py:143`, `extension/content.js:1129-1130` | H | M | yes |
| 6 | Cold start | Every start runs `create_all`, an Alembic subprocess (a second Python process that imports the models) and a table inspection, even when the schema is current | `backend/app/main.py:163-210`, `backend/alembic/env.py:11-12` | H | M | yes |
| 7 | Quota | The inoculation step makes an LLM call on every `/message` with manipulation score above 0.2 and is never cached | `api.py:190-198,217-218` | M | S | yes |
| 8 | Security | The rate limiter trusts the first `X-Forwarded-For` value, which the client can set. Buckets are keyed by full path, so `/history/sessions/1`, `/2`… each get their own allowance | `middleware.py:66-68,89` | M | S | yes |
| 9 | Security | These endpoints need no sign-in and run database queries: `/viral/*`, `/analytics/trends/*`, `/analytics/model/*`, `/analytics/business/summary`, `/analytics/users/leaderboard`, `/metrics`. The extension calls none of them | `routes/viral_routes.py:26,157,209`, `routes/analytics_routes.py:29-540`, `routes/metrics_routes.py:29` | M | S | yes |
| 10 | Build | `langchain`, `langchain-community`, `langchain-core`, `langchain-openai` and `langgraph` are installed but only `app/graph/workflow.py` uses them, and nothing imports that file. (Correction: `pandas` stays; `training/retrain_from_feedback.py`, which the server runs, needs it.) `pytest` and `tabulate` are in the production list | `backend/requirements.txt` | M | S | yes |
| 11 | Extension | `web_accessible_resources` exposes every popup page and script to all websites, but `content.js` never calls `getURL`. Any site can detect the extension and frame its pages | `extension/manifest.json` (last block) | M | S | yes |
| 12 | Extension | `host_permissions` include `*.railway.app`, `*.fly.dev` and all of `*.onrender.com`; the CSP has `connect-src *`. Only one backend host is used | `extension/manifest.json`, `extension/env.js:13` | M | S | yes |
| 13 | Reliability | On a cold backend the service worker aborts after 25 s of silence and the card shows "taking longer than usual" with no automatic retry | `extension/background/service_worker.js:253`, `extension/content.js:927-931` | M | S | yes |
| 14 | Quota | `/message` writes memory through a second path that makes up to 6 separate embedding calls (1 claim + 5 sources). The stream path batches them in one call | `api.py:577-621`, `retrieval/vector_store.py:82,171` | M | M | yes |
| 15 | Quota | Every uncached card check starts the early "knowledge" answer and the grounded answer, so 2 LLM calls where 1 often suffices | `stream_routes.py:186,237` | M | S | yes (trade-off) |
| 16 | Hosting | Each installed browser pings the backend every 4 minutes, all day. That keeps Render awake (good for speed) but uses about 730 of the 750 free instance hours. If the Gemini proxy is in the same Render workspace, the pool can run out before month end | `service_worker.js:40,66`, `render.yaml:42` | M | S | check |
| 17 | Security | A tracked file documents a test login (`test@test.com` / `test123`). If that account exists in production, it is a public login | `TEST_ACCOUNT_SETUP.md:11-12` | M | S | yes |
| 18 | Bug | Adversarial-input cleaning runs after the pipeline has already finished, so the cleaned text is never analysed | `api.py:328` then `api.py:350-360` | L | S | yes |
| 19 | Speed | `/message` loads every message of the session, then keeps the last 12. Session create, user message save and assistant save are separate commits to Neon | `api.py:263-282`, `api.py:798` | L | S | yes |
| 20 | Neon | The hourly scheduler runs database queries around the clock, waking Neon 24 times a day even with no users | `main.py:323-344` | L | S | yes |
| 21 | Security | (Withdrawn: signup also only requires 6 characters, so reset and signup already match) | `routes/auth_routes.py:181` vs `:27` | L | S | yes |
| 22 | Security | `python-jose 3.3.0` has published CVEs (fixed in 3.4.0). Our HS256-only use limits the exposure | `backend/requirements.txt` | L | S | yes |
| 23 | Security | CORS accepts any browser extension. The extension ID is now locked, so it can be pinned | `main.py:392` | L | S | yes |
| 24 | Input | `/check/stream` has no explicit length cap; `/message` rejects over 2000 characters. I did not check whether `_sanitize` caps it | `stream_routes.py:315`, `api.py:250` | L | S | yes |
| 25 | Dead code | `service_worker_enhanced.js` and `onnx_inference.js` are not in the manifest and are referenced only by each other | `extension/background/` | L | S | yes |
| 26 | Dead code | Root-level `popup.css`, `review.js`, `explain.html` and `voice.html` have no references. Root `popup.html`, `popup.js`, `login.js`, `dashboard.html` and `review.html` share names with the `popup/` files the manifest uses; confirm the two `popup.html` mentions in the service worker point at `popup/` before deleting | `extension/` root | L | S | yes |
| 27 | Dead code | `verify_popup.py` ships inside the extension folder | `extension/popup/verify_popup.py` | L | S | yes |
| 28 | Dead code | `app/graph/`, `app/rag/` and `app/agents/` are imported by nothing outside themselves | `backend/app/` | L | S | yes (keep if on roadmap) |
| 29 | Dead code | Two rate-limit systems exist. `rate_limit.py` (367 lines) is used only for response headers and the quota page | `backend/app/rate_limit.py`, `main.py:403` | L | M | yes |
| 30 | Repo | Four old extension zips (about 5.5 MB) are tracked next to the current one. `extension-version.json` still points at v2.6.3 | `factcheckai-website/public/` | L | S | yes |
| 31 | Repo | The current zip is 4.2 MB; the older ones were 125 KB. Not investigated; worth checking what is being packed | `factcheckai-website/public/truvanta-v2.6.4.zip` | L | S | yes |
| 32 | Repo | Root `requirements.txt` lists `torch` and `gradio` (it looks like the ML server's file). About 20 stale notes sit in `docs/`, `deployment-docs/` and the repo root | repo root | L | S | yes |
| 33 | Stale | The API reports version 2.6.1 and stores `model_version="2.6.1"`; the extension is 2.6.4 | `main.py:372`, `api.py:596` | L | S | yes |
| 34 | Startup | Two warm-ups do nothing on this host: the reranker and sentence-transformers need packages that are not installed | `main.py:122-126,259-266` | L | S | yes |
| 35 | Product | The backend has `/quota/usage`, but the extension never calls it, so users get no warning before a 429 | `routes/quota_routes.py`, `extension/` | L | M | yes |

## Fixes for the High items

**#1 Model reload per request.** Add a small getter in `app/analysis/ml.py` that returns the already-loaded model and vectorizer, and use it at `api.py:551`. This removes two disk reads and a temporary second copy of the model in RAM on each such request.

**#2 Anonymous access.** Change `/message` to require a signed-in user (`get_current_user`), and do the same for `/upload`, `/audio/transcribe`, `/audio/verify` and `/explain`. The popup redirects to login when there is no token, so normal use is unaffected. The evaluation runner and any API examples in the docs need a token afterwards.

**#3 Stream rate limit.** Add `"/check/stream": (10, 60)` to `_LIMITS`. Better, limit by user ID on this route, since `get_current_user_id` already decodes it. Pair this with #8 so the limit cannot be dodged with a fake header.

**#5 Reuse settled answers in the popup.** At the top of `do_grounded` (`api.py:144`), look up the `stream:` cache key and then `memory.lookup(text)`. If either has a settled verdict, build the `ai`, `evidence` and `grounded` values from it and skip the search and the LLM call. The classifier, manipulation and explainability steps still run, so the full report is unchanged.

**#6 Cold start.** Before the Alembic subprocess, read `alembic_version` with one query and compare it with the newest file in `alembic/versions/`. If they match, skip `create_all`, the subprocess and the inspection. Otherwise run them as today. This keeps deploys safe and makes wake-ups from sleep cheaper.

## Decisions that are yours

- **#15 Early answer.** It makes the card feel fast, and it is the fallback when sources fail. Dropping it halves LLM use per check. A middle option is to start it only if no published fact-check arrives in the first second. I did not check which provider it uses; if it shares Groq with the grounded call, that is where the daily limit will bite first.
- **#16 Keep-alive.** Decide whether you want the backend always awake. If yes, confirm the Gemini proxy is in a different Render workspace or is allowed to sleep. If no, raise the ping interval above 15 minutes and rely on `warmBackend()` in the card.
- **#28 Agentic code.** ARCHITECTURE.md lists moving `/message` onto the graph as roadmap. If that is still the plan, keep the code and only drop the packages from `requirements.txt` until then (#10).

## Don't do

- **Don't enable `fastembed`, `torch`, `transformers` or `sentence-transformers` on Render.** The app already uses about 320 MB of 512 MB (per ARCHITECTURE.md); each adds 100 MB or more.
- **Don't raise gunicorn workers above 1.** Every worker loads its own copy of the app and the in-memory cache stops being shared.
- **Don't turn on Redis** unless it is a free hosted tier with enough daily commands; the in-process cache plus pgvector memory already cover repeats.
- **Don't add paid search or LLM APIs** as fallbacks (SerpAPI, paid OpenRouter models). The model registry already rests models that need payment.
- **Don't keep Neon awake** with a database query in the health check or a frequent scheduler; the free compute hours would run out.
- **Don't move `/message` onto LangGraph now.** It adds the LangChain import cost to startup RAM for no user-visible gain.
- **Don't enable `SOCIAL_GRAPH_ENABLED` or `WIKIDATA_ENABLED`** in production: the first needs paid X API access, the second loads a large NER model.
