// Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
// Licensed under the Apache License, Version 2.0
// SPDX-License-Identifier: Apache-2.0
// Project: TruvantaAI � https://github.com/BharatChandra-sys/fake-news-extension
// ── Backend API URL ───────────────────────────────────────────
// Comes from ../env.js (USE_LOCAL_BACKEND). For a one-off production test
// without editing env.js: localStorage.setItem("FORCE_PRODUCTION", "true").
const _IS_PROD = !USE_LOCAL_BACKEND || localStorage.getItem("FORCE_PRODUCTION") === "true";
const API = _IS_PROD ? TRUVANTA_PROD_API : TRUVANTA_LOCAL_API;

const API_TIMEOUT_MS = 45000;  // 45s for AI reasoning tasks
const CLIENT_NAME = "edge-extension";
const CLIENT_VERSION = (chrome?.runtime?.getManifest?.().version) || "unknown";

// Debug: log which API is being used
console.log(`[TruvantaAI] API endpoint: ${API} (prod=${_IS_PROD})`);

function buildHeaders(extra = {}) {
	return {
		"X-Client": CLIENT_NAME,
		"X-Client-Version": CLIENT_VERSION,
		...extra,
	};
}

async function apiFetch(path, opts = {}, timeoutMs = API_TIMEOUT_MS) {
	const controller = new AbortController();
	const timer = setTimeout(() => controller.abort(), timeoutMs);
	const url = path.startsWith("http") ? path : `${API}${path}`;
	try {
		return await fetch(url, { ...opts, signal: controller.signal });
	} finally {
		clearTimeout(timer);
	}
}

async function readJsonSafe(res) {
	try {
		return await res.json();
	} catch (_) {
		return null;
	}
}

function getApiEndpoint() {
	return API;
}

// Export to window for cross-script access
if (typeof window !== 'undefined') {
	window.API = API;
	window.buildHeaders = buildHeaders;
	window.apiFetch = apiFetch;
	window.readJsonSafe = readJsonSafe;
	window.getApiEndpoint = getApiEndpoint;
}
