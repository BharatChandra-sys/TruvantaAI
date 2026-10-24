// Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
// Licensed under the Apache License, Version 2.0
// SPDX-License-Identifier: Apache-2.0
// ── Which backend the extension talks to ──────────────────────
// The single place to switch between your local backend and production.
// Loaded by every popup page (before config.js) and by the background
// worker, which also carries the in-page card's requests.
//
//   true  → http://127.0.0.1:8000   (run the backend with uvicorn first)
//   false → Render production       (use this before building the ZIP)
const USE_LOCAL_BACKEND = false;

const TRUVANTA_PROD_API = "https://factcheckai-coq3.onrender.com";
// 127.0.0.1, not localhost: on Windows "localhost" tries IPv6 first and can stall.
const TRUVANTA_LOCAL_API = "http://127.0.0.1:8000";
const TRUVANTA_API = USE_LOCAL_BACKEND ? TRUVANTA_LOCAL_API : TRUVANTA_PROD_API;
