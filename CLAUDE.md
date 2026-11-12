# TruvantaAI (formerly FactCheckAI) — Codebase Map

Read this first. Open a file only when the task needs it. Long-form detail lives in `docs/ARCHITECTURE.md` (pipeline, models, RAG) and `docs/API.md`. Don't read those unless the task needs it.

## What it is
A Chrome MV3 extension that fact-checks selected text. It talks to a FastAPI backend that searches live evidence, looks up past checks in pgvector memory and asks an LLM for a grounded verdict. There is also a Next.js marketing/install site.

## Top-level layout
| Path | What | Notes |
|---|---|---|
| `extension/` | MV3 extension, vanilla JS, v2.6.4 | **Main work area** |
| `backend/` | FastAPI, Python 3.11.9 | Render free tier (512 MB), Neon Postgres + pgvector |
| `factcheckai-website/` | Next.js 16 / React 19 / Tailwind 4 / three.js | Vercel. Has its own `AGENTS.md`: Next 16 has breaking changes, so read `node_modules/next/dist/docs/` before editing |
| `ml-servers/` | HF Space ensemble (`huggingface-ensemble/`), `oracle-deberta/` | Separate deploys |
| `gemini-proxy/` | Third-party Gemini web→API proxy (vendored) | Rarely touched |
| `docs/` | ARCHITECTURE, API, PRODUCT_PLAN | `docs/CLAUDE.md` is a superdesign prompt, **not** project info |
| `launch-video/` | HyperFrames launch video | Untracked |
| Root `*.md` summaries, `rd_tmp.txt`, `sr2.txt`, `voices.txt` | Scratch/notes | Ignore |
| `extension_private_key.pem`, `gen_ext_key.py` | Extension signing key | **Never commit or print the .pem** |

## Extension (`extension/`)
- `env.js`: **the single backend switch**. `USE_LOCAL_BACKEND = false` → `https://factcheckai-coq3.onrender.com`, `true` → `http://127.0.0.1:8000`. CI fails unless it is `false`.
- `popup/config.js`: `API`, `apiFetch` (45 s timeout), `buildHeaders` (`X-Client`, `X-Client-Version`). Loaded after env.js on every popup page.
- `manifest.json`: the `key` field locks the extension ID; don't change it. Has OAuth client_id, commands (Ctrl+Shift+Y/U/L), sidePanel = popup.html, content script on `<all_urls>`. There is no `web_accessible_resources` block (nothing on a web page loads extension files); host permissions and `connect-src` list only the backend host, localhost and Google sign-in, so a new backend host must be added to both.
- `background/service_worker.js` (354 lines): context menu, commands, alarms, `onConnect` port **"truvanta-check"** that relays the SSE stream from `POST /check/stream` to the card. Message types: `TEXT_SELECTED`, `OPEN_POPUP_WITH_TEXT`, `PING_BACKEND`, `OPEN_LOGIN`, `TRUVANTA_API`, `GET_API_BASE`, `SET_API_BASE`, `TRUVANTA_CHECK`.
- `content.js` (1220 lines, one IIFE, Shadow DOM): selection toolbar → floating card. Key functions: `showToolbar`, `openCard`, `runCheck`, `streamCheck` (port to the SW), `liveSources`/`liveFactcheck`/`liveEarly` (stream events), `renderResult`, `askFollowUp`, `renderSignIn`, `openFullReport`. **Content scripts must not fetch the backend directly** because CORS rejects page origins. Go through the SW.
- `popup/`: one HTML+JS pair per page: `popup` (chat, 1714 lines, main), `login`, `dashboard`, `history`, `saved`, `settings`, `detail`, `review`, `viral`. Plus `websocket_client.js`, `icons.js`, `shared.css`, `tailwind.css` (built from `extension/tailwind.input.css`).
  - popup.js key functions: `send()` → `POST /message`, `_renderFactCard`, `loadSessions`/`switchSession` (history API), `authFetch`, `submitFeedback`, voice functions (`startVoiceRecording` etc.), friction UI (`showViralPanicInterstitial`, `showHighConcernFriction`).
- **Auth:** `popup/login.js` uses `chrome.identity.launchWebAuthFlow` with the `https://<ext-id>.chromiumapp.org/oauth2` redirect (implicit token) → `POST /auth/google` → stores `{token, user}` in `chrome.storage.local`. Only one auth flow may run at a time (guarded).
- `chrome.storage.local` keys: `token`, `user`, `selectedText`, `pendingAnalysis`, `currentSessionId`, `savedClaims`, `detailData`, `analysisCache`, `pref_scores`, `pref_autocheck`, `frictionAnalytics`.
- Release: bump `manifest.json` version, zip `extension/` → `factcheckai-website/public/truvanta-vX.Y.Z.zip`, update `public/extension-version*.json`.

## Backend (`backend/`)
- Entry: `app/main.py` (startup, CORS, middleware, a background thread with a 14-minute keep-alive and hourly data collection, router includes). Run locally with `uvicorn app.main:app --reload` from `backend/`. Prod runs gunicorn with 1 worker (see root `render.yaml`).
- Config: `app/core/config.py` + `.env` (template: `backend/.env.example`). Flags: `SKIP_TRAIN_ON_STARTUP`, `REDIS_ENABLED`, `WIKIDATA_ENABLED`, `SOCIAL_GRAPH_ENABLED`, `ENABLE_DOCS`, `EMBEDDINGS_BACKEND` (gemini|local), `ML_SERVER_1_URL`/`ML_SERVER_2_URL`.
- DB: `backend/database.py`, `app/models.py` (SQLAlchemy), migrations in `alembic/versions/`.
- **Two request paths:**
  1. `routes/stream_routes.py` → `POST /check/stream` (SSE events: `sources`, `factcheck`, `verdict`, `done`). Used by the in-page card. `_run()` does a memory lookup in parallel with live search → LLM → `_persist()`.
  2. `api.py` → `POST /message`. Used by popup chat. `_run_pipeline_parallel` runs ML + AI + evidence + manipulation → `logic/decision.py` (calibrated fusion).
- Core modules (`app/analysis/`): `search.py` (evidence sources, key-term extraction, source health), `ai.py` + `ai_config.py` + `model_registry.py` (LLM providers Groq → Gemini/OpenRouter, models discovered at runtime, never hard-coded), `evidence.py`, `evidence_guard.py` (evidence overrides the model), `ml.py`/`ml_ensemble.py`/`transformer.py` (classifier fallback chain, TF-IDF in `data/*.joblib`), `manipulation.py`, `cooldown.py` (friction score). The rest are optional extras, so see the table in ARCHITECTURE.md.
- `app/retrieval/memory.py`: pgvector claim memory (VERIFIED/MODEL_ONLY/DISPUTED, instant answer at ≥0.97 similarity). `embeddings.py`, `hybrid.py`, `reranker.py`, `vector_store.py`.
- `app/graph/` (LangGraph, 9 nodes) and `app/rag/`, `app/agents/`: built but **not on any request path**.
- Routers and prefixes: `/auth` (signup, login, google, me, forgot/reset-password), `/history/sessions…`, `/stats`, `/explain`, `/review`, `/ab`, `/ws/connect`, `/cache`, `/quota`, `/analytics`, `/audio` (transcribe, verify), `/viral`, `/upload`, health (`/health/ping`), metrics, plus `api.py` (`/message`, `/feedback`, `/credibility`, `/velocity/stats`, `/clustering/stats`). The auth dependency is `get_current_user_id` in `app/auth.py`.
- Sign-in is required on `/message`, `/check/stream`, `/upload`, `/audio/*`, `/explain`, `/viral/*`, `/analytics/*`, `/metrics` (they spend free-tier quota or query the DB). Rate limits live in `app/middleware.py` (`_LIMITS`), counted per token when signed in, per IP otherwise.
- Dependencies: `requirements.txt` is production; `requirements-dev.txt` adds pytest. `pandas` is needed by `training/retrain_from_feedback.py`.
- `/message` reuses a verdict already settled from sources (`_settled_answer` in `api.py`: the card's `stream:` cache, then claim memory) instead of searching again. Startup skips table creation and Alembic when `_schema_is_current()` (`main.py`) says the DB is at head with all tables.
- Chat context: `conversation_context()` in `analysis/chat.py` is the context window (newest 12 messages, 6,000 characters total, 1,500 per message). `/message` takes history from the saved session when `session_id` is given (popup), otherwise from the `history` the client sent (the in-page card, which saves no chat session).
- `EARLY_ANSWER` is off by default (it costs a second model call per card check); set `EARLY_ANSWER=true` to get the one-second early answer back. `ALLOW_FRESH_CHECKS=true` is needed on a server being evaluated.
- Tests: `cd backend && pytest tests -q` (CI env: `DATABASE_URL=sqlite:///./test.db JWT_SECRET=x SKIP_TRAIN_ON_STARTUP=true REDIS_ENABLED=false ENVIRONMENT=test`). Eval: `backend/eval/run_eval.py`.

## CI/CD (`.github/workflows/`)
- `ci.yml` (push to main, PRs): backend pytest, extension checks (`node --check`, `.github/scripts/check-manifest.js`, `env.js` must have `USE_LOCAL_BACKEND = false`), website type-check (lint is report-only: 28 known errors), bandit + pip-audit report.
- Backend deploy: Render, only after CI passes (`autoDeployTrigger: checksPass` in `render.yaml`). Website: Vercel Git integration.
- `release.yml`: pushing tag `vX.Y.Z` (must equal the manifest version) builds the extension ZIP and creates a GitHub Release.

## Conventions / gotchas
- Every source file starts with an Apache-2.0 copyright header ("Bodapati Bharat Chandra"). Keep it on new files.
- Branding: the user-facing name is **TruvantaAI**. Old names (FactCheckAI) remain in paths, service names and the website folder. Don't rename paths.
- Windows dev box: use `127.0.0.1`, not `localhost`.
- Memory budget: prod has 512 MB, so don't add heavy local models to the default path.
- Commit messages look like `fix: …`, `release: vX.Y.Z — …`.
