// Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
// Licensed under the Apache License, Version 2.0
// SPDX-License-Identifier: Apache-2.0
// Project: TruvantaAI � https://github.com/BharatChandra-sys/fake-news-extension
// Viral Spread Monitor
// config.js is loaded before this file and provides: API, apiFetch, buildHeaders, readJsonSafe

// Safety fallback in case config.js didn't load
if (typeof apiFetch === "undefined") {
  const _API = (typeof API !== "undefined") ? API : "https://factcheckai-coq3.onrender.com";
  window.apiFetch = async (path, opts = {}) => fetch(_API + path, opts);
  window.buildHeaders = (extra = {}) => extra;
  window.readJsonSafe = async (res) => { try { return await res.json(); } catch { return null; } };
}
  
let refreshTimer = null;

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function timeAgo(iso) {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ── Navigation ────────────────────────────────────────────────
document.getElementById("back-btn").addEventListener("click", () => {
  window.location.href = chrome.runtime.getURL("popup/popup.html");
});

const refreshBtn = document.getElementById("refresh-btn");
refreshBtn.addEventListener("click", () => {
  refreshBtn.classList.add("spinning");
  loadViralData().finally(() => {
    setTimeout(() => refreshBtn.classList.remove("spinning"), 600);
  });
});

// ── Load data ─────────────────────────────────────────────────
async function loadViralData() {
  try {
    const [velocityRes, clusterRes] = await Promise.allSettled([
      apiFetch("/velocity/stats"),
      apiFetch("/clustering/stats"),
    ]);

    // Velocity stats
    if (velocityRes.status === "fulfilled" && velocityRes.value.ok) {
      const data = await readJsonSafe(velocityRes.value) || {};
      const stats = data.stats || {};
      const topViral = data.top_viral || [];

      document.getElementById("stat-viral").textContent   = stats.viral_claims   ?? 0;
      document.getElementById("stat-trending").textContent = stats.trending_claims ?? 0;
      document.getElementById("stat-total").textContent   = stats.total_claims_tracked ?? 0;
      document.getElementById("stat-checks").textContent  = stats.total_timestamps ?? 0;

      renderViralClaims(topViral);
      renderChart(topViral);
    }

    // Clustering stats
    if (clusterRes.status === "fulfilled" && clusterRes.value.ok) {
      const data = await readJsonSafe(clusterRes.value) || {};
      renderTrendingClusters(data.top_clusters || []);
    }

  } catch (e) {
    console.error("Viral data load failed:", e);
  }
}

// ── Render viral claims ───────────────────────────────────────
function renderViralClaims(claims) {
  const list = document.getElementById("viral-claims-list");
  if (!claims.length) {
    list.innerHTML = `
      <div class="viral-empty">
        <div class="viral-empty-icon">🛡️</div>
        <div style="font-size:13px;color:var(--t2)">No viral claims detected</div>
        <div style="font-size:11px;color:var(--t3);margin-top:4px">All clear right now</div>
      </div>`;
    return;
  }

  list.innerHTML = claims.slice(0, 5).map(c => {
    const velPct = Math.round((c.velocity_5min || 0) * 100);
    return `
      <div class="viral-claim-card">
        <div class="viral-claim-header">
          <span class="viral-badge viral">
            <span class="material-symbols-outlined ms-10">warning</span>
            Viral
          </span>
          <span style="font-size:11px;color:var(--t3);margin-left:auto">${c.count_5min || 0}/5min</span>
        </div>
        <div class="viral-claim-text">${esc((c.claim_hash || "").slice(0, 16))}…</div>
        <div class="viral-velocity-bar">
          <div class="viral-velocity-fill" style="width:${velPct}%"></div>
        </div>
        <div class="viral-claim-meta">
          <div class="viral-claim-meta-item">
            <span class="material-symbols-outlined ms-10">trending_up</span>
            ${c.count_1hr || 0}/hr
          </div>
        </div>
      </div>`;
  }).join("");
}

// ── Render trending clusters ──────────────────────────────────
function renderTrendingClusters(clusters) {
  const list = document.getElementById("trending-claims-list");
  if (!clusters.length) {
    list.innerHTML = `
      <div class="viral-empty">
        <div style="font-size:13px;color:var(--t2)">No trending clusters</div>
      </div>`;
    return;
  }

  list.innerHTML = clusters.slice(0, 5).map(c => `
    <div class="viral-claim-card">
      <div class="viral-claim-header">
        <span class="viral-badge trending">
          <span class="material-symbols-outlined ms-10">trending_up</span>
          ${c.size || 0} claims
        </span>
        ${c.campaign_score > 0.5
          ? `<span class="viral-badge viral" style="margin-left:4px">Coordinated</span>`
          : ""}
      </div>
      <div class="viral-claim-meta">
        <div class="viral-claim-meta-item">
          <span class="material-symbols-outlined ms-10">hub</span>
          Cluster #${c.cluster_id ?? "?"}
        </div>
        <div class="viral-claim-meta-item">
          <span class="material-symbols-outlined ms-10">percent</span>
          ${Math.round((c.campaign_score || 0) * 100)}% campaign
        </div>
      </div>
    </div>`).join("");
}

// ── Render velocity chart ─────────────────────────────────────
function renderChart(topViral) {
  const bars = document.getElementById("chart-bars");
  if (!topViral.length) {
    bars.innerHTML = `<div style="width:100%;text-align:center;font-size:11px;color:var(--t3);padding-top:40px">No data yet</div>`;
    return;
  }

  const maxCount = Math.max(...topViral.map(c => c.count_5min || 1), 1);
  bars.innerHTML = topViral.slice(0, 12).map((c, i) => {
    const h = Math.round(((c.count_5min || 0) / maxCount) * 100);
    const isViral = (c.velocity_5min || 0) > 0.5;
    return `
      <div class="viral-chart-bar ${isViral ? "has-viral" : ""}"
           style="height:${Math.max(h, 4)}%"
           title="${c.count_5min || 0} checks in 5min">
        <span class="viral-chart-label">${i + 1}</span>
      </div>`;
  }).join("");
}

// ── Init ──────────────────────────────────────────────────────
loadViralData();

// Auto-refresh every 30 seconds — only when the page is visible
function startPolling() {
  if (refreshTimer) return;
  refreshTimer = setInterval(() => {
    if (document.visibilityState === "visible") loadViralData();
  }, 30000);
}

function stopPolling() {
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
}

startPolling();
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") {
    loadViralData();   // immediate refresh on tab focus
    startPolling();
  } else {
    stopPolling();
  }
});

// Clean up on page unload
window.addEventListener("unload", stopPolling);
