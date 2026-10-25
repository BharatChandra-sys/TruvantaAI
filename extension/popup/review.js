// Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
// Licensed under the Apache License, Version 2.0
// SPDX-License-Identifier: Apache-2.0
// Project: TruvantaAI � https://github.com/BharatChandra-sys/fake-news-extension
// Review Queue — TruvantaAI
// Self-contained: does not rely on any globals from config.js

const _REVIEW_API = (function () {
  // Try to use the API constant from config.js if available, else fallback to production
  if (typeof API !== "undefined") return API;
  return "https://factcheckai-coq3.onrender.com";
})();

async function _reviewFetch(path, opts = {}) {
  const url = _REVIEW_API + path;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20000);
  try {
    return await fetch(url, { ...opts, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function _reviewJson(res) {
  try { return await res.json(); } catch { return null; }
}

function _reviewHeaders(extra = {}) {
  return {
    "X-Client": "Truvanta-extension",
    ...extra,
  };
}

// ─────────────────────────────────────────────────────────────

let currentFilter = "all";
let reviewQueue   = [];

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ── Navigation ────────────────────────────────────────────────
document.getElementById("back-btn").addEventListener("click", () => {
  window.location.href = chrome.runtime.getURL("popup/popup.html");
});

document.getElementById("refresh-btn").addEventListener("click", loadReviewQueue);

document.querySelectorAll(".review-filter-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".review-filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentFilter = btn.dataset.filter;
    loadReviewQueue();
  });
});

// ── Stats ─────────────────────────────────────────────────────
async function loadStats() {
  try {
    const { token } = await chrome.storage.local.get("token");
    if (!token) return;

    const res = await _reviewFetch("/review/stats", {
      headers: _reviewHeaders({ "Authorization": `Bearer ${token}` }),
    });
    if (!res.ok) return;
    const data = await _reviewJson(res) || {};

    document.getElementById("stat-pending").textContent  = data.total_pending       ?? "-";
    document.getElementById("stat-today").textContent    = data.reviewed_today      ?? "-";
    document.getElementById("stat-priority").textContent = data.high_priority_count ?? "-";
  } catch (e) {
    console.warn("Stats load failed:", e.message);
  }
}

// ── Queue ─────────────────────────────────────────────────────
async function loadReviewQueue() {
  const content = document.getElementById("review-content");
  content.innerHTML = `
    <div class="review-loading">
      <div class="spin-ring"></div>
      <div style="margin-top:12px;font-size:12px;color:var(--t3)">Loading review queue...</div>
    </div>`;

  try {
    const { token } = await chrome.storage.local.get("token");
    if (!token) { window.location.href = chrome.runtime.getURL("popup/login.html"); return; }

    const res = await _reviewFetch(`/review/queue?priority=${currentFilter}&limit=20`, {
      headers: _reviewHeaders({ "Authorization": `Bearer ${token}` }),
    });

    if (res.status === 401) { window.location.href = chrome.runtime.getURL("popup/login.html"); return; }
    if (!res.ok) throw new Error(`Server error ${res.status}`);

    reviewQueue = await _reviewJson(res) || [];

    if (!reviewQueue.length) {
      content.innerHTML = `
        <div class="empty-state">
          <span class="material-symbols-outlined ms-24" style="color:var(--accent);margin-bottom:8px">check_circle</span>
          <div style="font-size:13px;color:var(--t2)">No claims to review</div>
          <div style="font-size:11px;color:var(--t3);margin-top:4px">All ${esc(currentFilter)} claims have been reviewed</div>
        </div>`;
      return;
    }

    renderQueue();
    loadStats();
  } catch (e) {
    content.innerHTML = `
      <div class="error-state">
        <span class="material-symbols-outlined ms-24" style="color:var(--fake)">error</span>
        <div style="font-size:13px;color:var(--t2);margin-top:8px">Failed to load review queue</div>
        <div style="font-size:11px;color:var(--t3);margin-top:4px">${esc(e.message)}</div>
      </div>`;
  }
}

function renderQueue() {
  const content = document.getElementById("review-content");
  content.innerHTML = "";
  reviewQueue.forEach(item => content.appendChild(createCard(item)));
}

// ── Card ──────────────────────────────────────────────────────
function createCard(item) {
  const card = document.createElement("div");
  card.className = "review-card" + (item.already_reviewed ? " review-card-reviewed" : "");

  const confPct = Math.round((item.confidence || 0) * 100);
  const mlPct   = Math.round((item.ml_score   || 0) * 100);
  const aiPct   = item.ai_score       != null ? Math.round(item.ai_score * 100)       : null;
  const evPct   = item.evidence_score != null ? Math.round(item.evidence_score * 100) : null;

  let badges = "";
  if (item.is_viral)                          badges += `<span class="priority-badge priority-viral">Viral</span>`;
  if (item.is_trending)                       badges += `<span class="priority-badge priority-trending">Trending</span>`;
  if (item.cluster_size && item.cluster_size > 5) badges += `<span class="priority-badge priority-cluster">${item.cluster_size} similar</span>`;

  const vClass = item.current_verdict === "fake" ? "v-fake" : item.current_verdict === "real" ? "v-real" : "v-uncertain";

  card.innerHTML = `
    <div class="review-card-header">
      <div class="review-card-verdict ${vClass}">${esc(item.current_verdict.toUpperCase())}</div>
      <div class="review-card-conf">${confPct}%</div>
    </div>
    ${badges ? `<div class="review-card-badges">${badges}</div>` : ""}
    <div class="review-card-claim">${esc(item.claim_text)}</div>
    <div class="review-card-scores">
      <div class="review-score-item">
        <span class="review-score-label">ML</span>
        <div class="review-score-bar"><div class="review-score-fill" style="width:${mlPct}%;background:${mlPct > 50 ? "var(--fake)" : "var(--real)"}"></div></div>
        <span class="review-score-val">${mlPct}%</span>
      </div>
      ${aiPct != null ? `
      <div class="review-score-item">
        <span class="review-score-label">AI</span>
        <div class="review-score-bar"><div class="review-score-fill" style="width:${aiPct}%;background:var(--accent)"></div></div>
        <span class="review-score-val">${aiPct}%</span>
      </div>` : ""}
      ${evPct != null ? `
      <div class="review-score-item">
        <span class="review-score-label">Evidence</span>
        <div class="review-score-bar"><div class="review-score-fill" style="width:${evPct}%;background:${evPct > 50 ? "var(--real)" : "var(--fake)"}"></div></div>
        <span class="review-score-val">${evPct}%</span>
      </div>` : ""}
    </div>
    ${item.already_reviewed
      ? `<div class="review-card-reviewed-note"><span class="material-symbols-outlined ms-12">check_circle</span> Already reviewed</div>`
      : `<div class="review-card-actions">
           <button class="review-btn review-btn-real"><span class="material-symbols-outlined ms-14">check_circle</span> Real</button>
           <button class="review-btn review-btn-fake"><span class="material-symbols-outlined ms-14">cancel</span> Fake</button>
           <button class="review-btn review-btn-skip"><span class="material-symbols-outlined ms-14">skip_next</span> Skip</button>
         </div>`}
    <div class="review-card-meta">
      <span class="material-symbols-outlined ms-12">schedule</span>
      ${formatDate(item.created_at)}
    </div>`;

  if (!item.already_reviewed) {
    card.querySelector(".review-btn-real").addEventListener("click", () => submitReview(item.id, "real", card));
    card.querySelector(".review-btn-fake").addEventListener("click", () => submitReview(item.id, "fake", card));
    card.querySelector(".review-btn-skip").addEventListener("click", () => skipCard(card));
  }
  return card;
}

// ── Submit ────────────────────────────────────────────────────
async function submitReview(claimId, verdict, card) {
  card.querySelectorAll(".review-btn").forEach(b => b.disabled = true);
  try {
    const { token } = await chrome.storage.local.get("token");
    const res = await _reviewFetch("/review/submit", {
      method: "POST",
      headers: _reviewHeaders({ "Content-Type": "application/json", "Authorization": `Bearer ${token}` }),
      body: JSON.stringify({ claim_id: claimId, verdict }),
    });
    if (!res.ok) throw new Error(`Server error ${res.status}`);

    card.innerHTML = `
      <div class="review-success">
        <span class="material-symbols-outlined ms-24" style="color:var(--real)">check_circle</span>
        <div style="font-size:13px;color:var(--t1);margin-top:8px">Review submitted!</div>
        <div style="font-size:11px;color:var(--t3);margin-top:4px">Verdict: ${verdict.toUpperCase()}</div>
      </div>`;

    setTimeout(() => {
      card.style.cssText = "opacity:0;transform:translateX(-20px);transition:all .3s";
      setTimeout(() => {
        card.remove();
        if (!document.querySelector(".review-card")) loadReviewQueue();
      }, 300);
    }, 1400);

    loadStats();
  } catch (e) {
    card.querySelectorAll(".review-btn").forEach(b => b.disabled = false);
    const err = document.createElement("div");
    err.className = "review-error";
    err.textContent = "Failed: " + e.message;
    card.appendChild(err);
    setTimeout(() => err.remove(), 3000);
  }
}

function skipCard(card) {
  card.style.cssText = "opacity:0;transform:translateX(20px);transition:all .3s";
  setTimeout(() => {
    card.remove();
    if (!document.querySelector(".review-card")) loadReviewQueue();
  }, 300);
}

function formatDate(iso) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1)  return "Just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  if (d < 7)  return `${d}d ago`;
  return new Date(iso).toLocaleDateString();
}

// ── Init ──────────────────────────────────────────────────────
chrome.storage.local.get("token", ({ token }) => {
  if (!token) { window.location.href = chrome.runtime.getURL("popup/login.html"); return; }
  loadStats();
  loadReviewQueue();
});
