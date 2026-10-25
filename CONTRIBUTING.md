<!-- Copyright 2027 Bodapati Bharat Chandra. All rights reserved. -->
<!-- Licensed under the Apache License, Version 2.0 | SPDX-License-Identifier: Apache-2.0 -->

# Contributing to Truvanta

Thanks for helping. This page gets you from a fresh clone to a working change in about ten minutes.

## Set up

### Backend

With Python 3.11:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

Without a `DATABASE_URL` the backend uses a local SQLite file; vectors are then stored as JSON and similarity search is skipped, everything else works. All the keys are free. The ones that matter:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string. Use a development database, never production. |
| `JWT_SECRET` | Signing key for login tokens (`openssl rand -hex 32`) |
| `GROQ_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY` | Language model providers; any one is enough |
| `GOOGLE_FACTCHECK_API_KEY` | Published fact-checks (free Google Cloud key, no billing needed) |
| `GOOGLE_CLIENT_ID` | Google sign-in |
| `NEWS_REGION`, `NEWS_LANG`, `NEWS_CEID` | Google News edition, default India (`IN`, `en-IN`, `IN:en`) |
| `REDIS_ENABLED`, `REDIS_URL` | Optional shared cache and rate limits |
| `TAVILY_API_KEY` | Optional extra web search |
| `BREVO_API_KEY`, `SMTP_USER` | Password-reset email |

### Extension

1. In `extension/env.js`, set `USE_LOCAL_BACKEND = true`.
2. Open `chrome://extensions`, turn on **Developer mode**, click **Load unpacked** and choose the `extension` folder.
3. After editing, reload the extension there and refresh open tabs.

Set `USE_LOCAL_BACKEND` back to `false` before committing; CI checks it.

## Check your change

```bash
cd backend
python -m pytest tests -q          # unit tests, about 10 seconds
python eval/run_eval.py --limit 20 # end-to-end on 20 labelled claims, needs the server running
```

If you touch search, ranking or the verdict prompt, run the full evaluation (`python eval/run_eval.py`) before and after, and put both summaries in the pull request. A change that raises accuracy but also raises the wrong-verdict rate is not an improvement: a wrong answer costs more than an "Uncertain".

CI runs the backend tests, syntax-checks every extension script and validates the manifest on each push and pull request.

## Pull requests

- Branch from `main`.
- Use conventional commit prefixes: `feat:`, `fix:`, `docs:`, `test:`, `perf:`, `refactor:`.
- Describe what you changed and how you tested it. For UI changes, include a screenshot.
- Never commit API keys or `.env` files.

## Good places to start

- **Add claims to the evaluation set** (`backend/eval/claims.jsonl`), especially recent news, non-English claims and claims that should come back Uncertain.
- **Detect non-claims** (song titles, headings, opinions) before searching, so they get a clear "not a factual claim" message.
- **A new free evidence source** in `backend/app/analysis/search.py`, behind the existing circuit breaker.
- **Firefox support** for the extension.

## Reporting bugs

Open an issue with the claim you checked, what the card showed, and what you expected. For security issues, follow [SECURITY.md](SECURITY.md) instead.
