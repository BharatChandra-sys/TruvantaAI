<!-- Copyright 2027 Bodapati Bharat Chandra. All rights reserved. -->
<!-- Licensed under the Apache License, Version 2.0 | SPDX-License-Identifier: Apache-2.0 -->

# API

Base URL: `https://factcheckai-coq3.onrender.com`, or `http://127.0.0.1:8000` locally. All check endpoints require a bearer token.

On Render's free tier the backend sleeps after 15 minutes without traffic, so the first request after a quiet period can take 30 to 60 seconds.

## Sign up or log in

```bash
curl -X POST $API/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"...","name":"Your Name"}'
# {"token": "eyJ...", "user": {...}}

curl -X POST $API/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"..."}'
```

`POST /auth/google` accepts a Google `id_token` (web) or `access_token` (extension).

## Real-time check: `POST /check/stream`

Server-Sent Events. This is what the in-page card uses.

```bash
curl -N -X POST $API/check/stream \
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

| Event | When | Notes |
|---|---|---|
| `start` | Immediately | Echoes the claim |
| `sources` | Each time a source answers | Can arrive several times; append, don't replace |
| `factcheck` | First published fact-check found | An early answer, before the model has read anything |
| `judging` | Search finished | `count` passages go to the model |
| `verdict` | Final | `verdict` is `real`, `fake` or `uncertain`; `cached: true` on a repeat check |
| `done` | Last | Total time in ms |
| `error` | On failure | A user-facing message |

Each item in `evidence_articles` carries `url`, `title`, `source`, `stance` (`support`, `contradict`, `neutral`), `cited`, `kind`, `rating`, `published` and `low_trust`. The numbers in the explanation's `[n]` citations are 1-based indexes into this list.

## Full pipeline and chat: `POST /message`

Used by the popup.

```bash
curl -X POST $API/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"...", "check": true, "session_id": 12}'
```

`check: true` skips the chat-or-claim classification step. The response adds the classifier, manipulation and explainability signals to the verdict. `session_id` continues an existing chat; `image_url` attaches an image to the claim.

## Other endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness |
| `GET /history/sessions` | The signed-in user's chats |
| `GET /history/sessions/{id}/messages` | Messages in one chat, including fact-check cards |
| `POST /feedback` | A user's correction to a verdict; feeds continuous learning |

## Rate limits

Per client, per minute: `/message` 20, `/feedback` 20, `/auth/login` 10, `/auth/signup` 5, everything else 60. Limits are enforced when Redis is available.
