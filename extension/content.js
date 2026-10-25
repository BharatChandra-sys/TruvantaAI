// Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
// Licensed under the Apache License, Version 2.0
// SPDX-License-Identifier: Apache-2.0
// Project: TruvantaAI - https://github.com/BharatChandra-sys/fake-news-extension
(() => {
  if (window.__TruvantaContentLoaded) return;
  window.__TruvantaContentLoaded = true;

  // Clean up UI injected by older versions
  ["__Truvanta_tooltip__", "__Truvanta_floating_toolbar__", "__Truvanta_quick_popup__", "__Truvanta_inline_chat__"]
    .forEach(id => document.getElementById(id)?.remove());

  const MAX_SOURCES = 6;            // source rows shown in the card
  const MIN_SCAN_MS = 700;          // keep the searching state from flickering
  const PING_EVERY_MS = 60000;      // wake the backend at most once a minute
  const MIN_SELECTION = 20;

  // ══════════════════════════════════════════════════════════
  // Styles: same tokens and motion as the Truvanta landing page
  // ══════════════════════════════════════════════════════════
  const CSS = `
    :host { all: initial; }
    * { box-sizing: border-box; margin: 0; padding: 0; }

    .ui {
      --canvas: #0a0a0b; --panel: #17171a; --panel-2: #1f1f23;
      --line: rgba(255,255,255,0.08); --line-strong: rgba(255,255,255,0.14);
      --fg: #ededef; --fg-2: #a1a1aa; --fg-3: #6b6b73;
      --accent: #ffc53d; --accent-hover: #ffd465; --on-accent: #1a1300;
      --true: #3dd68c; --false: #ff6166; --unsure: #a1a1aa;
      --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
      --ease-sheet: cubic-bezier(0.32, 0.72, 0, 1);
      --sans: -apple-system, BlinkMacSystemFont, "Segoe UI Variable Text", "Segoe UI", Inter, Roboto, sans-serif;
      --mono: ui-monospace, "SF Mono", "Cascadia Mono", Menlo, Consolas, monospace;
      position: absolute;
      font-family: var(--sans);
      color: var(--fg);
      -webkit-font-smoothing: antialiased;
      text-align: left;
      line-height: 1.4;
    }
    .elevated {
      background: var(--panel);
      box-shadow: 0 0 0 1px rgba(255,255,255,0.06), 0 24px 64px -16px rgba(0,0,0,0.6), 0 8px 24px -8px rgba(0,0,0,0.4);
    }
    button { font: inherit; color: inherit; background: none; border: 0; cursor: pointer; }
    button:focus-visible, a:focus-visible, input:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
    svg { display: block; }

    /* ── Toolbar ─────────────────────────────── */
    .toolbar {
      display: flex; align-items: center; gap: 2px; padding: 4px;
      border-radius: 12px;
      opacity: 0; transform: translateY(4px);
      transition: opacity 200ms var(--ease-out), transform 200ms var(--ease-out),
                  left 220ms var(--ease-out), top 220ms var(--ease-out);
    }
    .toolbar.placing { transition: opacity 200ms var(--ease-out), transform 200ms var(--ease-out); }
    .toolbar.leaving { opacity: 0; transform: scale(0.96); transition-duration: 160ms; }
    .toolbar.in { opacity: 1; transform: none; }
    .check-btn {
      display: flex; align-items: center; gap: 7px; height: 30px; padding: 0 12px 0 9px;
      border-radius: 9px; background: #ededef; color: #0a0a0b;
      font-size: 13px; font-weight: 600; letter-spacing: -0.01em;
      transition: background-color 120ms var(--ease-out), transform 120ms var(--ease-out);
    }
    .check-btn:hover { background: #ffffff; }
    .icon-btn {
      display: grid; place-items: center; width: 30px; height: 30px; border-radius: 8px; color: var(--fg-2);
      transition: background-color 120ms var(--ease-out), color 120ms var(--ease-out), transform 120ms var(--ease-out);
    }
    .icon-btn:hover { background: rgba(255,255,255,0.06); color: var(--fg); }
    .check-btn:active, .icon-btn:active, .send:active, .retry:active { transform: scale(0.97); }
    .divider { width: 1px; height: 16px; margin: 0 3px; background: var(--line); }

    /* ── Card ────────────────────────────────── */
    .card {
      width: 360px; max-width: calc(100vw - 16px);
      border-radius: 16px; overflow: hidden;
      opacity: 0; transform: translateY(12px);
      transform-origin: top left;
      transition: opacity 400ms var(--ease-sheet), transform 500ms var(--ease-sheet),
                  height 320ms var(--ease-sheet), top 320ms var(--ease-sheet);
    }
    .card.in { opacity: 1; transform: none; }
    .card.out { opacity: 0; transform: translateY(8px); transition-duration: 200ms; }
    .card.instant { transition: none !important; }
    .inner { padding: 16px; }
    .card.morph .inner { opacity: 0; }
    .card.in .inner { opacity: 1; transition: opacity 260ms var(--ease-out) 120ms; }
    .head { cursor: grab; touch-action: none; user-select: none; }
    .card.dragging .head { cursor: grabbing; }
    .card.dragging { transition: none; }
    .head { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin: -16px -16px 0; padding: 16px 16px 0; }
    .brand { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; letter-spacing: -0.01em; }
    .head-right { display: flex; align-items: center; gap: 6px; }
    .meta { font-family: var(--mono); font-size: 11px; color: var(--fg-3); }
    .close { width: 26px; height: 26px; }
    .claim {
      margin-top: 12px; padding-left: 12px; border-left: 2px solid var(--line-strong);
      font-size: 13px; line-height: 1.45; color: var(--fg-2);
      display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
    }
    .body {
      margin-top: 16px; max-height: min(52vh, 440px); overflow-y: auto;
      margin-right: -10px; padding-right: 10px;      /* keep the scrollbar off the content */
      scrollbar-width: thin; scrollbar-color: rgba(255,255,255,0.14) transparent;
    }
    .body:hover { scrollbar-color: rgba(255,255,255,0.24) transparent; }
    /* Browsers without scrollbar-color support */
    .body::-webkit-scrollbar { width: 6px; }
    .body::-webkit-scrollbar-track { background: transparent; }
    .body::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.14); border-radius: 999px; }
    .body::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.24); }
    .body::-webkit-scrollbar-button { display: none; height: 0; }
    .fade { animation: fade-up 220ms var(--ease-out) both; }
    @keyframes fade-up { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }

    .scan-label { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--fg-2); }
    .scan-note { margin-top: 10px; font-size: 12px; line-height: 1.45; color: var(--fg-3); animation: fade-up 300ms var(--ease-out) both; }
    .stagger { opacity: 0; animation: fade-up 300ms var(--ease-out) forwards; }
    .live-row { animation: fade-up 260ms var(--ease-out) both; }
    .prelim {
      display: flex; align-items: center; gap: 10px; margin-bottom: 12px; padding: 10px;
      border-radius: 10px; background: rgba(10,10,11,0.5); box-shadow: inset 0 0 0 1px var(--line);
      animation: fade-up 300ms var(--ease-out) both;
    }
    .prelim-text { font-size: 12px; color: var(--fg-2); }
    .signin { padding: 4px 0 2px; }
    .signin-title { font-size: 14px; font-weight: 600; color: var(--fg); letter-spacing: -0.01em; }
    .signin-text { margin-top: 6px; font-size: 13px; line-height: 1.5; color: var(--fg-2); }
    .signin-btn {
      margin-top: 14px; height: 34px; padding: 0 16px; border-radius: 9px;
      background: #ededef; color: #0a0a0b; font-size: 13px; font-weight: 600;
      transition: background-color 120ms var(--ease-out), transform 120ms var(--ease-out), opacity 120ms;
    }
    .signin-btn:hover { background: #ffffff; }
    .signin-btn:active { transform: scale(0.97); }
    .signin-btn:disabled { opacity: 0.6; cursor: default; }
    .signin-hint { margin-top: 10px; font-size: 12px; color: var(--fg-3); }
    .icon-btn.done { color: var(--true); }
    .pulse { width: 6px; height: 6px; border-radius: 50%; background: var(--fg-2); animation: pulse 1.2s ease-in-out infinite; }
    @keyframes pulse { 0%, 100% { opacity: 0.3; } 50% { opacity: 1; } }
    .rows { display: flex; flex-direction: column; gap: 6px; margin-top: 12px; }
    .row {
      display: flex; align-items: center; gap: 10px; min-height: 36px; padding: 8px 10px;
      border-radius: 8px; background: rgba(10,10,11,0.5);
    }
    .scan-row { justify-content: space-between; opacity: 0; animation: fade-in 250ms var(--ease-out) forwards; }
    @keyframes fade-in { to { opacity: 1; } }
    .skel { height: 8px; border-radius: 4px; background: var(--panel-2); }
    .track { width: 56px; height: 3px; border-radius: 2px; background: var(--panel-2); overflow: hidden; }
    .track > span {
      display: block; height: 100%; border-radius: 2px; background: var(--fg-3);
      transform: scaleX(0); transform-origin: left;
      animation: fill 900ms var(--ease-out) forwards;
    }
    @keyframes fill { to { transform: scaleX(1); } }

    .verdict-row { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
    .chip {
      display: inline-flex; align-items: center; gap: 6px; height: 24px; padding: 0 10px;
      border-radius: 999px; font-size: 12px; font-weight: 500; letter-spacing: 0.01em;
    }
    .chip i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
    .chip.true { color: var(--true); background: rgba(61,214,140,0.12); }
    .chip.false { color: var(--false); background: rgba(255,97,102,0.12); }
    .chip.unsure { color: var(--unsure); background: rgba(161,161,170,0.12); }
    .conf { font-family: var(--mono); font-size: 12px; color: var(--fg-2); }
    .bar { margin-top: 12px; height: 3px; border-radius: 2px; background: var(--panel-2); overflow: hidden; }
    .bar > span {
      display: block; height: 100%; border-radius: 2px; transform-origin: left; transform: scaleX(0);
      transition: transform 500ms var(--ease-out) 50ms;
    }
    .bar > span.true { background: var(--true); }
    .bar > span.false { background: var(--false); }
    .bar > span.unsure { background: var(--unsure); }
    .summary { margin-top: 12px; font-size: 13px; line-height: 1.5; color: var(--fg-2); white-space: pre-line; }
    .summary strong { color: var(--fg); font-weight: 600; }
    .sources { margin-top: 12px; }
    .source { text-decoration: none; color: inherit; opacity: 0; animation: fade-up 300ms var(--ease-out) forwards; transition: background-color 120ms var(--ease-out); }
    .source:hover { background: rgba(255,255,255,0.05); }
    .tile {
      display: grid; place-items: center; flex: none; width: 20px; height: 20px; border-radius: 5px;
      background: var(--panel-2); color: var(--fg-2); font-size: 10px; font-weight: 600; text-transform: uppercase;
    }
    .src-name { flex: 1; min-width: 0; font-size: 12px; color: var(--fg); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .src-domain { flex: none; max-width: 40%; font-family: var(--mono); font-size: 11px; color: var(--fg-3); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .empty { font-size: 12px; color: var(--fg-3); }
    .basis { margin-top: 12px; padding: 8px 10px; border-radius: 8px; background: var(--panel-2); font-size: 12px; line-height: 1.5; color: var(--fg-3); }

    .error { font-size: 13px; line-height: 1.5; color: var(--fg-2); }
    .retry {
      margin-top: 12px; height: 30px; padding: 0 12px; border-radius: 8px; background: var(--panel-2);
      font-size: 12px; font-weight: 500; color: var(--fg);
      transition: background-color 120ms var(--ease-out), transform 120ms var(--ease-out);
    }
    .retry:hover { background: #2a2a2f; }

    .thread { display: flex; flex-direction: column; gap: 10px; }
    .thread:not(:empty) { margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--line); }
    .msg { font-size: 13px; line-height: 1.5; animation: fade-up 220ms var(--ease-out) both; white-space: pre-line; }
    .msg.user { align-self: flex-end; max-width: 85%; padding: 8px 12px; border-radius: 12px; background: var(--panel-2); color: var(--fg); }
    .msg.bot { color: var(--fg-2); }
    .msg.bot strong { color: var(--fg); font-weight: 600; }
    .msg.typing { display: flex; gap: 4px; padding: 4px 0; }
    .msg.typing i { width: 5px; height: 5px; border-radius: 50%; background: var(--fg-3); animation: pulse 1.2s ease-in-out infinite; }
    .msg.typing i:nth-child(2) { animation-delay: 0.15s; }
    .msg.typing i:nth-child(3) { animation-delay: 0.3s; }

    .foot { margin-top: 14px; }
    .ask {
      display: flex; align-items: center; gap: 6px; padding: 4px 4px 4px 12px;
      border-radius: 10px; background: rgba(10,10,11,0.6); box-shadow: inset 0 0 0 1px var(--line);
      transition: box-shadow 120ms var(--ease-out);
    }
    .ask:focus-within { box-shadow: inset 0 0 0 1px var(--line-strong); }
    .ask input {
      flex: 1; min-width: 0; height: 30px; border: 0; outline: none; background: transparent;
      font: inherit; font-size: 13px; color: var(--fg);
    }
    .ask input::placeholder { color: var(--fg-3); }
    .send {
      display: grid; place-items: center; width: 30px; height: 30px; border-radius: 8px;
      background: var(--fg); color: var(--canvas);
      transition: opacity 120ms var(--ease-out), transform 120ms var(--ease-out);
    }
    .send:disabled { opacity: 0.35; cursor: default; }
    .links { display: flex; justify-content: space-between; align-items: center; margin-top: 10px; }
    .link {
      display: inline-flex; align-items: center; gap: 3px; font-size: 12px; color: var(--fg-2);
      transition: color 120ms var(--ease-out);
    }
    .link:hover { color: var(--fg); }
    .hint { font-family: var(--mono); font-size: 11px; color: var(--fg-3); }

    /* ── Toast ───────────────────────────────── */
    .toast {
      padding: 8px 14px; border-radius: 999px; font-size: 12px; font-weight: 500; white-space: nowrap;
      opacity: 0; transform: translateY(-6px);
      transition: opacity 200ms var(--ease-out), transform 200ms var(--ease-out);
    }
    .toast.in { opacity: 1; transform: none; }

    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { animation-duration: 1ms !important; animation-delay: 0ms !important; transition-duration: 1ms !important; }
      .toolbar, .card, .toast { transform: none !important; }
    }
  `;

  // ══════════════════════════════════════════════════════════
  // Icons
  // ══════════════════════════════════════════════════════════
  // Flat Truvanta logo. `mono` draws it in one colour (e.g. on the amber button).
  function markSvg(height, pixels = true, underlay = "#17171a", mono = null) {
    const width = Math.round(height * 40 / 31);
    const fg = mono || "#ededef";
    const accent = mono || "#ffc53d";
    return `
      <svg width="${width}" height="${height}" viewBox="0 0 40 31" fill="none" aria-hidden="true">
        <path d="M11.6 9.6V24.6C11.6 27.5 13.2 29.2 16.2 29.2" stroke="${fg}" stroke-width="4"/>
        <path d="M10.4 9.4 19.4 20.6 33.6 7.4" stroke="${underlay}" stroke-width="6.6" stroke-linejoin="round"/>
        <path d="M10.4 9.4 19.4 20.6 33.6 7.4" stroke="${accent}" stroke-width="4.2" stroke-linejoin="round"/>
        <path d="M0.4 11.4C1.8 5.6 4.6 2.4 9.6 2.4H32.4L26 9.2H10.6C6.4 9.2 3 9.9 0.4 11.4Z" fill="${fg}"/>
        <path d="M0.4 11.4C1.8 5.6 4.6 2.4 9.6 2.4H12.4C8.2 3 5.6 5.4 4.4 9.6 2.8 10 1.4 10.6 0.4 11.4Z" fill="${accent}"/>
        ${pixels ? `<g fill="#ffc53d">
          <rect x="37.2" y="0.2" width="2.7" height="2.7" rx="0.5"/>
          <rect x="34.2" y="3" width="1.9" height="1.9" rx="0.4"/>
          <rect x="36.3" y="5.8" width="2.1" height="2.1" rx="0.4"/>
          <rect x="34.8" y="10.2" width="2" height="2" rx="0.4" fill-opacity="0.55"/>
        </g>` : ""}
      </svg>`;
  }

  const ICONS = {
    tick: `<svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M3.5 8.5 6.5 11.5 12.5 4.5"/></svg>`,
    copy: `<svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"><rect x="5.5" y="5.5" width="8" height="8" rx="2"/><path d="M10.5 5.5V4a1.5 1.5 0 0 0-1.5-1.5H4A1.5 1.5 0 0 0 2.5 4v5A1.5 1.5 0 0 0 4 10.5h1.5"/></svg>`,
    highlight: `<svg width="15" height="15" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="m9.5 3 3.5 3.5-5.5 5.5H4v-3.5z"/><path d="M2.5 14h11"/></svg>`,
    close: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M4 4l8 8M12 4l-8 8"/></svg>`,
    send: `<svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M8 13V3M3.5 7.5 8 3l4.5 4.5"/></svg>`,
    chevron: `<svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3.5 10.5 8 6 12.5"/></svg>`,
  };

  // ══════════════════════════════════════════════════════════
  // Shadow root host
  // ══════════════════════════════════════════════════════════
  let host = null;
  let root = null;

  function ensureRoot() {
    if (host?.isConnected) return root;
    host = document.createElement("truvanta-root");
    host.style.cssText = "all:initial;position:absolute;top:0;left:0;width:0;height:0;z-index:2147483647;";
    root = host.attachShadow({ mode: "open" });
    const style = document.createElement("style");
    style.textContent = CSS;
    root.appendChild(style);
    document.documentElement.appendChild(host);
    return root;
  }

  function isInsideUi(event) {
    return !!host && event.composedPath().includes(host);
  }

  // ══════════════════════════════════════════════════════════
  // Helpers
  // ══════════════════════════════════════════════════════════
  function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  function escapeHtml(s) {
    return String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  // Escaped text with **bold** support only.
  function richText(s) {
    return escapeHtml(s).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  }

  function domainOf(url) {
    try { return new URL(url).hostname.replace(/^www\./, ""); } catch { return ""; }
  }

  function selectionRect() {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return null;
    const r = sel.getRangeAt(0).getBoundingClientRect();
    if (!r.width && !r.height) return null;
    return { left: r.left + scrollX, right: r.right + scrollX, top: r.top + scrollY, bottom: r.bottom + scrollY };
  }

  function clampX(x, width) {
    return Math.min(Math.max(x, scrollX + 8), scrollX + document.documentElement.clientWidth - width - 8);
  }

  // Requests go through the background worker: from here they would carry
  // the website's origin and be rejected by the backend's CORS policy.
  // `check: true` tells the backend this is a fact-check request, so it skips
  // its chat-vs-claim classification. Follow-up questions are chat.
  async function postMessage(message, history, check = false) {
    let res;
    try {
      res = await chrome.runtime.sendMessage({
        type: "TRUVANTA_API",
        path: "/message",
        body: { message, history, session_id: null, check },
      });
    } catch {
      throw new Error("Truvanta was updated. Refresh this page to keep checking.");
    }
    if (!res) throw new Error("Couldn’t reach Truvanta. Try again in a moment.");
    if (res.error === "timeout") throw new Error("This is taking longer than usual. Try again in a moment.");
    if (res.error) throw new Error("Couldn’t reach Truvanta. Check your connection and try again.");
    if (res.status === 401) throw new NotSignedIn();
    if (res.status === 429) throw new Error("Too many requests. Wait a moment and try again.");
    if (!res.ok) throw new Error(`The server returned an error (${res.status}). Try again in a moment.`);
    return res.data;
  }

  // ══════════════════════════════════════════════════════════
  // Toast
  // ══════════════════════════════════════════════════════════
  function showToast(message) {
    const r = ensureRoot();
    const toast = el("div", "ui toast elevated", message);
    toast.setAttribute("role", "status");
    r.appendChild(toast);
    toast.style.top = `${scrollY + 16}px`;
    toast.style.left = `${scrollX + document.documentElement.clientWidth / 2 - toast.offsetWidth / 2}px`;
    requestAnimationFrame(() => toast.classList.add("in"));
    setTimeout(() => {
      toast.classList.remove("in");
      setTimeout(() => toast.remove(), 200);
    }, 1600);
  }


  const wait = ms => new Promise(r => setTimeout(r, ms));

  // ══════════════════════════════════════════════════════════
  // Backend warm-up: the server sleeps when idle, so nudge it
  // as soon as the user selects something.
  // ══════════════════════════════════════════════════════════
  let lastPing = 0;
  function warmBackend() {
    const now = Date.now();
    if (now - lastPing < PING_EVERY_MS) return;
    lastPing = now;
    try { chrome.runtime.sendMessage({ type: "PING_BACKEND" })?.catch?.(() => {}); } catch { /* extension reloaded */ }
  }

  // ══════════════════════════════════════════════════════════
  // Toolbar (appears on text selection)
  // ══════════════════════════════════════════════════════════
  let toolbar = null;
  let toolbarText = "";

  function showToolbar(text, pointerX) {
    const rect = selectionRect();
    if (!rect) return;
    toolbarText = text;
    warmBackend();
    const r = ensureRoot();
    const fresh = !toolbar;
    if (fresh) {
      toolbar = el("div", "ui toolbar elevated placing");
      toolbar.setAttribute("role", "toolbar");
      toolbar.setAttribute("aria-label", "Truvanta");
      toolbar.innerHTML = `
        <button class="check-btn" data-action="check" title="Check this claim">${markSvg(13, false, "#ededef", "#0a0a0b")}<span>Check</span></button>
        <div class="divider"></div>
        <button class="icon-btn" data-action="copy" title="Copy" aria-label="Copy">${ICONS.copy}</button>
        <button class="icon-btn" data-action="highlight" title="Highlight" aria-label="Highlight">${ICONS.highlight}</button>
        <button class="icon-btn" data-action="close" title="Close" aria-label="Close">${ICONS.close}</button>`;
      // Keep the page selection alive while clicking toolbar buttons
      toolbar.addEventListener("mousedown", e => e.preventDefault());
      toolbar.addEventListener("click", onToolbarClick);
      r.appendChild(toolbar);
    }
    const width = toolbar.offsetWidth || 190;
    const height = toolbar.offsetHeight || 38;
    const above = rect.top - scrollY > height + 16;
    const centerX = pointerX ?? (rect.left + rect.right) / 2;
    // A visible toolbar glides to the new selection; a new one fades in place.
    toolbar.style.left = `${clampX(centerX - width / 2, width)}px`;
    toolbar.style.top = `${above ? rect.top - height - 10 : rect.bottom + 10}px`;
    if (fresh) {
      const node = toolbar;
      requestAnimationFrame(() => {
        node.classList.add("in");
        requestAnimationFrame(() => node.classList.remove("placing"));
      });
    }
  }

  function toolbarBox() {
    if (!toolbar) return null;
    return {
      left: parseFloat(toolbar.style.left) || 0,
      top: parseFloat(toolbar.style.top) || 0,
      width: toolbar.offsetWidth,
      height: toolbar.offsetHeight,
    };
  }

  function hideToolbar() {
    if (!toolbar) return;
    const node = toolbar;
    toolbar = null;
    node.classList.remove("in");
    node.classList.add("leaving");
    setTimeout(() => node.remove(), 200);
  }

  function flashDone(btn) {
    const original = btn.innerHTML;
    btn.innerHTML = ICONS.tick;
    btn.classList.add("done");
    btn.setAttribute("aria-label", "Copied");
    setTimeout(() => {
      btn.innerHTML = original;
      btn.classList.remove("done");
      btn.setAttribute("aria-label", "Copy");
    }, 1200);
  }

  function onToolbarClick(e) {
    const btn = e.target.closest("button");
    if (!btn) return;
    const text = window.getSelection().toString().trim() || toolbarText;
    switch (btn.dataset.action) {
      case "check":
        if (text) openCard(text, { from: toolbarBox() });
        hideToolbar();
        break;
      case "copy":
        if (text) navigator.clipboard.writeText(text).then(() => flashDone(btn), () => showToast("Couldn’t copy"));
        break;
      case "highlight":
        highlightSelection();
        hideToolbar();
        break;
      case "close":
        hideToolbar();
        break;
    }
  }

  function highlightSelection() {
    const sel = window.getSelection();
    if (!sel || sel.rangeCount === 0) return;
    const mark = document.createElement("mark");
    mark.style.cssText = "background:rgba(255,197,61,0.3);color:inherit;border-radius:2px;padding:0 1px;";
    try {
      sel.getRangeAt(0).surroundContents(mark);
      sel.removeAllRanges();
    } catch {
      showToast("Select text within one paragraph to highlight");
    }
  }

  // ══════════════════════════════════════════════════════════
  // Card (fact-check result + follow-up)
  // ══════════════════════════════════════════════════════════
  let card = null;
  const cache = new Map();   // selected text → last result, for instant re-opens

  const VERDICT = {
    real: { cls: "true", label: "True" },
    true: { cls: "true", label: "True" },
    fake: { cls: "false", label: "False" },
    false: { cls: "false", label: "False" },
  };

  function openCard(text, { from = null } = {}) {
    closeCard(true);
    const anchor = selectionRect();
    const r = ensureRoot();

    const node = el("div", "ui card elevated instant");
    node.setAttribute("role", "dialog");
    node.setAttribute("aria-label", "Truvanta fact check");
    node.innerHTML = `
      <div class="inner">
        <div class="head">
          <div class="brand">${markSvg(14, false)}<span>Truvanta</span></div>
          <div class="head-right">
            <span class="meta">checking…</span>
            <button class="icon-btn close" data-action="close" aria-label="Close">${ICONS.close}</button>
          </div>
        </div>
        <p class="claim"></p>
        <div class="body" aria-live="polite">
          <div class="result"></div>
          <div class="thread"></div>
        </div>
        <div class="foot" hidden>
          <form class="ask">
            <input type="text" placeholder="Ask a follow-up…" aria-label="Ask a follow-up question" />
            <button class="send" type="submit" aria-label="Send" disabled>${ICONS.send}</button>
          </form>
          <div class="links">
            <button class="link" data-action="open">Open full report ${ICONS.chevron}</button>
            <span class="hint">Esc to close</span>
          </div>
        </div>
      </div>`;
    node.querySelector(".claim").textContent = text;
    r.appendChild(node);
    const inner = node.querySelector(".inner");

    card = {
      node,
      inner,
      text,
      anchor,
      above: false,
      dragged: false,
      history: [{ role: "user", content: text }],
      busy: false,
      timers: [],
      ro: null,
    };

    node.querySelector('[data-action="close"]').addEventListener("click", () => closeCard());
    node.querySelector('[data-action="open"]').addEventListener("click", () => openFullReport(text));
    const form = node.querySelector(".ask");
    const input = form.querySelector("input");
    const send = form.querySelector(".send");
    input.addEventListener("input", () => { send.disabled = !input.value.trim() || card?.busy; });
    form.addEventListener("submit", e => {
      e.preventDefault();
      const q = input.value.trim();
      if (!q || card?.busy) return;
      input.value = "";
      send.disabled = true;
      askFollowUp(q);
    });
    enableDrag(node, node.querySelector(".head"));

    const cached = cache.get(text);
    if (cached) renderResult(cached);
    else renderScanning();

    // The card's height follows its content, animated.
    card.ro = new ResizeObserver(syncHeight);
    card.ro.observe(inner);
    syncHeight();
    placeCard(true);

    // Entrance: grow out of the toolbar when there is one, otherwise rise in.
    if (from) {
      const dx = from.left - (parseFloat(node.style.left) || 0);
      const dy = from.top - (parseFloat(node.style.top) || 0);
      node.classList.add("morph");
      node.style.transform = `translate(${dx}px, ${dy}px) scale(0.9)`;
    }
    node.getBoundingClientRect();
    requestAnimationFrame(() => {
      node.classList.remove("instant");
      node.style.transform = "";
      node.classList.add("in");
    });

    if (!cached) runCheck();
  }

  function clearTimers(c = card) {
    if (!c) return;
    c.timers.forEach(clearTimeout);
    c.timers = [];
  }

  function closeCard(immediate = false) {
    if (!card) return;
    const { node, ro, port } = card;
    clearTimers();
    ro?.disconnect();
    try { port?.disconnect(); } catch { /* already closed */ }
    card = null;
    if (immediate) return node.remove();
    node.classList.remove("in");
    node.classList.add("out");
    setTimeout(() => node.remove(), 200);
  }

  function syncHeight() {
    if (!card) return;
    card.node.style.height = `${card.inner.offsetHeight}px`;
    if (card.above) placeCard();
  }

  // Place below the selection, or above it if there isn't room below.
  function placeCard(initial = false) {
    if (!card || card.dragged) return;
    const { node, inner, anchor } = card;
    const width = node.offsetWidth;
    const height = inner.offsetHeight;
    const viewTop = scrollY;
    const viewBottom = scrollY + innerHeight;
    const a = anchor || { left: scrollX + innerWidth / 2 - width / 2, top: scrollY + 80, bottom: scrollY + 80 };
    if (initial) {
      const spaceBelow = viewBottom - a.bottom;
      const spaceAbove = a.top - viewTop;
      card.above = spaceBelow < Math.max(height, 360) + 20 && spaceAbove > spaceBelow;
    }
    node.style.left = `${clampX(a.left, width)}px`;
    node.style.top = `${card.above ? Math.max(a.top - height - 12, viewTop + 8) : a.bottom + 12}px`;
    node.style.transformOrigin = card.above ? "bottom left" : "top left";
  }

  function enableDrag(node, handle) {
    handle.addEventListener("pointerdown", e => {
      if (e.button !== 0 || e.target.closest("button")) return;
      const startX = e.pageX;
      const startY = e.pageY;
      const left = parseFloat(node.style.left) || 0;
      const top = parseFloat(node.style.top) || 0;
      handle.setPointerCapture(e.pointerId);
      node.classList.add("dragging");
      const move = ev => {
        if (card?.node !== node) return;
        card.dragged = true;
        node.style.left = `${left + ev.pageX - startX}px`;
        node.style.top = `${top + ev.pageY - startY}px`;
      };
      const up = () => {
        node.classList.remove("dragging");
        handle.removeEventListener("pointermove", move);
        handle.removeEventListener("pointerup", up);
        handle.removeEventListener("pointercancel", up);
      };
      handle.addEventListener("pointermove", move);
      handle.addEventListener("pointerup", up);
      handle.addEventListener("pointercancel", up);
    });
  }

  function setMeta(text) {
    const meta = card?.node.querySelector(".meta");
    if (meta) meta.textContent = text;
  }

  function resultEl() {
    return card?.node.querySelector(".result");
  }

  function renderScanning() {
    const box = resultEl();
    if (!box) return;
    box.innerHTML = "";
    const wrap = el("div", "fade scan-wrap");
    const label = el("div", "scan-label");
    label.append(el("span", "pulse"), el("span", "label-text", "Searching sources"));
    const rows = el("div", "rows live-rows");
    [62, 48, 70, 54].forEach((w, i) => {
      const row = el("div", "row scan-row");
      row.style.animationDelay = `${i * 120}ms`;
      const skel = el("span", "skel");
      skel.style.width = `${w}%`;
      const track = el("span", "track");
      const fill = el("span");
      fill.style.animationDelay = `${100 + i * 120}ms`;
      track.appendChild(fill);
      row.append(skel, track);
      rows.appendChild(row);
    });
    wrap.append(label, rows);
    box.appendChild(wrap);

    // Be honest when the server is slow to wake up.
    const note = text => {
      let n = box.querySelector(".scan-note");
      if (!n) { n = el("p", "scan-note"); wrap.appendChild(n); }
      n.textContent = text;
    };
    clearTimers();
    card.timers.push(
      setTimeout(() => note("Still searching. The first check after a quiet spell can take up to a minute."), 6000),
      setTimeout(() => note("Almost there…"), 25000),
    );
  }

  function renderError(message, retry) {
    const box = resultEl();
    if (!box) return;
    clearTimers();
    setMeta("");
    box.innerHTML = "";
    const wrap = el("div", "fade");
    wrap.appendChild(el("p", "error", message));
    if (retry) {
      const btn = el("button", "retry", "Try again");
      btn.addEventListener("click", retry);
      wrap.appendChild(btn);
    }
    box.appendChild(wrap);
  }

  // Each block of the result rises in slightly after the one above it.
  function stagger(node, index) {
    node.classList.add("stagger");
    node.style.animationDelay = `${index * 60}ms`;
    return node;
  }

  function renderResult(data) {
    const box = resultEl();
    if (!box || !card) return;
    clearTimers();
    box.innerHTML = "";
    const summaryText = data.explanation || data.reply || "";
    let step = 0;

    if (data.is_claim === false) {
      // Not a checkable claim: show the reply on its own.
      setMeta("");
      const chip = el("span", "chip unsure");
      chip.append(el("i"), document.createTextNode("Not a factual claim"));
      box.appendChild(stagger(chip, step++));
    } else {
      const v = VERDICT[String(data.verdict || "").toLowerCase()] || { cls: "unsure", label: "Uncertain" };
      const pct = Math.max(0, Math.min(100, Math.round((Number(data.confidence) || 0) * 100)));

      const head = el("div", "verdict-row");
      const chip = el("span", `chip ${v.cls}`);
      chip.append(el("i"), document.createTextNode(v.label));
      head.append(chip, el("span", "conf", `${pct}% confidence`));
      box.appendChild(stagger(head, step++));

      const bar = el("div", "bar");
      const fill = el("span", v.cls);
      bar.appendChild(fill);
      box.appendChild(stagger(bar, step++));
      requestAnimationFrame(() => requestAnimationFrame(() => { fill.style.transform = `scaleX(${pct / 100})`; }));

      // Nothing found addressed the claim: the verdict comes from established
      // knowledge, so don't present unrelated search results as its evidence.
      const fromKnowledge = data.basis === "knowledge";
      const sources = fromKnowledge ? [] : collectSources(data);
      setMeta(fromKnowledge ? "no sources" : sources.length === 1 ? "1 source" : `${sources.length} sources`);
      if (summaryText) {
        const p = el("p", "summary");
        // Keep [n] only for sources listed below the summary.
        const shown = summaryText.replace(/\s*\[(\d+)\]/g, (m, n) => (Number(n) <= sources.length ? m : ""));
        p.innerHTML = richText(shown);
        box.appendChild(stagger(p, step++));
      }
      if (fromKnowledge) {
        box.appendChild(stagger(el("p", "basis", "No sources found for this claim. This answer is from established knowledge, so confidence is capped at 70%. Check recent claims elsewhere."), step++));
        card.history.push({ role: "assistant", content: summaryText });
        showFoot();
        return;
      }
      const list = el("div", "rows sources");
      if (sources.length) {
        sources.forEach(s => {
          const a = el("a", "row source");
          a.href = s.url;
          a.target = "_blank";
          a.rel = "noopener noreferrer";
          a.style.animationDelay = `${step++ * 60}ms`;
          // Numbered to match the [n] citations in the summary.
          a.append(el("span", "tile", String(list.children.length + 1)), el("span", "src-name", s.name || s.domain), el("span", "src-domain", s.domain));
          list.appendChild(a);
        });
      } else {
        list.appendChild(stagger(el("p", "empty", "No sources were returned for this check."), step++));
      }
      box.appendChild(list);
      card.history.push({ role: "assistant", content: summaryText });
      showFoot();
      return;
    }

    if (summaryText) {
      const p = el("p", "summary");
      p.innerHTML = richText(summaryText);
      box.appendChild(stagger(p, step++));
      card.history.push({ role: "assistant", content: summaryText });
    }
    showFoot();
  }

  function showFoot() {
    const foot = card?.node.querySelector(".foot");
    if (!foot || !foot.hidden) return;
    foot.hidden = false;
    stagger(foot, 4);
  }

  function collectSources(data) {
    const out = [];
    const seen = new Set();
    const articles = Array.isArray(data.evidence_articles) ? data.evidence_articles : [];
    const urls = Array.isArray(data.evidence) ? data.evidence : [];
    for (const a of articles) {
      if (!a || !a.url || seen.has(a.url)) continue;
      seen.add(a.url);
      const domain = domainOf(a.url);
      // Published fact-checks show their rating ("False", "Mostly true") instead of the domain.
      // Results whose "source" is just their domain read better under their page title.
      const named = a.source && a.source.toLowerCase().replace(/^www\./, "") !== domain ? a.source : a.title;
      // Low-reliability web results are labelled so they read as weaker evidence.
      out.push({ url: a.url, domain: a.rating || (a.low_trust ? `${domain} · low trust` : domain), name: named || domain });
    }
    for (const u of urls) {
      if (typeof u !== "string" || seen.has(u) || !/^https?:/i.test(u)) continue;
      seen.add(u);
      const domain = domainOf(u);
      out.push({ url: u, domain, name: domain });
    }
    return out.slice(0, MAX_SOURCES);
  }

  // ── Real-time check ─────────────────────────────────────────
  // The background worker relays /check/stream events over a port, so the
  // card can show sources and an early fact-check match while the verdict
  // is still being worked out.
  class StreamUnavailable extends Error {}

  function streamCheck(current, text, on) {
    return new Promise((resolve, reject) => {
      let port;
      try {
        port = chrome.runtime.connect({ name: "truvanta-check" });
      } catch {
        reject(new Error("Truvanta was updated. Refresh this page to keep checking."));
        return;
      }
      current.port = port;
      let settled = false;
      const finish = (fn, value) => {
        if (settled) return;
        settled = true;
        try { port.disconnect(); } catch { /* already closed */ }
        fn(value);
      };
      port.onMessage.addListener(({ event, data, status, reason }) => {
        switch (event) {
          case "sources": on.sources?.(data.items || []); break;
          case "factcheck": on.factcheck?.(data); break;
          case "judging": on.judging?.(data.count || 0); break;
          case "verdict": finish(resolve, data); break;
          case "error": finish(reject, new Error(data?.message || "The check failed. Try again in a moment.")); break;
          case "http_error":
            if (status === 404 || status === 405) finish(reject, new StreamUnavailable());
            else if (status === 401) finish(reject, new NotSignedIn());
            else if (status === 429) finish(reject, new Error("Too many requests. Wait a moment and try again."));
            else finish(reject, new Error(`The server returned an error (${status}). Try again in a moment.`));
            break;
          case "network_error":
            finish(reject, new Error(reason === "timeout"
              ? "This is taking longer than usual. Try again in a moment."
              : "Couldn’t reach Truvanta. Check your connection and try again."));
            break;
          case "end": finish(reject, new Error("The check ended without a result. Try again.")); break;
        }
      });
      port.onDisconnect.addListener(() => finish(reject, new Error("Couldn’t reach Truvanta. Try again in a moment.")));
      port.postMessage({ type: "START", text });
    });
  }

  const KIND_LABEL = { fact_check: "fact-check", reference: "reference", news: "news", web: "web" };

  // Swap a skeleton row for a real source as soon as it is found.
  function liveSources(items) {
    const box = resultEl();
    const rows = box?.querySelector(".live-rows");
    if (!rows || !card) return;
    card.liveUrls = card.liveUrls || new Set();
    for (const it of items) {
      if (!it.url || card.liveUrls.has(it.url) || card.liveUrls.size >= 5) continue;
      card.liveUrls.add(it.url);
      const name = it.source || domainOf(it.url) || "Source";
      const row = el("div", "row live-row");
      row.append(
        el("span", "tile", name.charAt(0)),
        el("span", "src-name", name),
        el("span", "src-domain", it.rating || KIND_LABEL[it.kind] || domainOf(it.url)),
      );
      const skeleton = rows.querySelector(".scan-row");
      if (skeleton) skeleton.replaceWith(row);
      else rows.appendChild(row);
    }
    setScanLabel(`Searching sources · ${card.liveUrls.size} found`);
  }

  // A published fact-check arrives well before the verdict: show it as an early answer.
  function liveFactcheck(fc) {
    const box = resultEl();
    const wrap = box?.querySelector(".scan-wrap");
    if (!wrap || wrap.querySelector(".prelim")) return;
    const cls = fc.stance === "contradict" ? "false" : fc.stance === "support" ? "true" : "unsure";
    const prelim = el("div", "prelim");
    const chip = el("span", `chip ${cls}`);
    chip.append(el("i"), document.createTextNode(fc.rating || "Rated"));
    const text = el("span", "prelim-text", `${fc.source || "A fact-checker"} rated a matching claim`);
    prelim.append(chip, text);
    wrap.insertBefore(prelim, wrap.firstChild);
  }

  function setScanLabel(text) {
    const label = resultEl()?.querySelector(".scan-label .label-text");
    if (label) label.textContent = text;
  }

  async function signedIn() {
    try {
      const { token } = await chrome.storage.local.get("token");
      return !!token;
    } catch {
      return false;
    }
  }

  // Shown instead of a result when the user isn't signed in (or their session expired).
  function renderSignIn(expired = false) {
    const box = resultEl();
    if (!box || !card) return;
    clearTimers();
    setMeta("");
    card.awaitingLogin = true;
    box.innerHTML = "";
    const wrap = el("div", "fade signin");
    wrap.append(
      el("p", "signin-title", expired ? "Your session has expired" : "Sign in to check claims"),
      el("p", "signin-text", "Truvanta checks claims against live sources and shows its evidence. "
        + "It's free; you just need an account."),
    );
    const btn = el("button", "signin-btn", "Sign in");
    btn.addEventListener("click", () => {
      try { chrome.runtime.sendMessage({ type: "OPEN_LOGIN" })?.catch?.(() => {}); }
      catch { showToast("Refresh this page, then try again"); return; }
      btn.textContent = "Waiting for sign-in…";
      btn.disabled = true;
    });
    wrap.append(btn, el("p", "signin-hint", "The check starts automatically once you're signed in."));
    box.appendChild(wrap);
  }

  class NotSignedIn extends Error {
    constructor() { super("Sign in to Truvanta to continue."); }
  }

  async function runCheck() {
    const current = card;
    if (!current) return;
    if (!(await signedIn())) {
      if (card === current) renderSignIn();
      return;
    }
    current.awaitingLogin = false;
    current.busy = true;
    renderScanning();
    setMeta("checking…");
    try {
      let data;
      try {
        [data] = await Promise.all([
          streamCheck(current, current.text, {
            sources: items => card === current && liveSources(items),
            factcheck: fc => card === current && liveFactcheck(fc),
            judging: n => card === current && setScanLabel(n ? `Reading ${n} source${n === 1 ? "" : "s"}` : "Weighing the evidence"),
          }),
          wait(MIN_SCAN_MS),
        ]);
      } catch (err) {
        if (!(err instanceof StreamUnavailable)) throw err;
        // Older backend without /check/stream: one request, same result.
        [data] = await Promise.all([postMessage(current.text, [], true), wait(MIN_SCAN_MS)]);
      }
      if (card !== current) return;
      if (data) {
        cache.set(current.text, data);
        if (cache.size > 30) cache.delete(cache.keys().next().value);
      }
      renderResult(data || {});
    } catch (err) {
      if (card !== current) return;
      if (err instanceof NotSignedIn) renderSignIn(true);
      else renderError(err.message, () => runCheck());
    } finally {
      if (card === current) current.busy = false;
    }
  }

  // Resume a check as soon as the user signs in from the login window.
  try {
    chrome.storage.onChanged.addListener((changes, area) => {
      if (area === "local" && changes.token?.newValue && card?.awaitingLogin) runCheck();
    });
  } catch { /* not running as an extension */ }

  async function askFollowUp(question) {
    if (!card) return;
    const current = card;
    const thread = current.node.querySelector(".thread");
    const body = current.node.querySelector(".body");
    thread.appendChild(el("div", "msg user", question));
    const typing = el("div", "msg typing");
    typing.append(el("i"), el("i"), el("i"));
    thread.appendChild(typing);
    body.scrollTo({ top: body.scrollHeight, behavior: "smooth" });

    current.busy = true;
    try {
      const data = await postMessage(question, current.history);
      if (card !== current) return;
      const reply = data?.reply || data?.explanation || "I couldn’t answer that. Try rephrasing.";
      const msg = el("div", "msg bot");
      msg.innerHTML = richText(reply);
      typing.replaceWith(msg);
      current.history.push({ role: "user", content: question }, { role: "assistant", content: reply });
      if (current.history.length > 20) current.history = current.history.slice(-20);
    } catch (err) {
      if (card !== current) return;
      typing.replaceWith(el("div", "msg bot", err.message));
    } finally {
      if (card === current) {
        current.busy = false;
        const input = current.node.querySelector(".ask input");
        current.node.querySelector(".send").disabled = !input.value.trim();
        input.focus();
        body.scrollTo({ top: body.scrollHeight, behavior: "smooth" });
      }
    }
  }

  function openFullReport(text) {
    chrome.storage.local.set({ selectedText: text, pendingAnalysis: true }, () => {
      chrome.runtime.sendMessage({ type: "OPEN_POPUP_WITH_TEXT", text })?.catch?.(() => {});
    });
  }

  // ══════════════════════════════════════════════════════════
  // Events
  // ══════════════════════════════════════════════════════════

  // Debounce timer for TEXT_SELECTED messages: fires once, 300ms after a
  // selection settles, instead of flooding the service worker
  let selectionDebounce = null;

  function handleSelection(pointerX) {
    const selected = window.getSelection().toString().trim();
    if (card && card.text === selected) return;   // its card is already open
    if (selected.length > MIN_SELECTION) {
      showToolbar(selected, pointerX);
      clearTimeout(selectionDebounce);
      selectionDebounce = setTimeout(() => {
        try { chrome.runtime.sendMessage({ type: "TEXT_SELECTED", payload: selected })?.catch?.(() => {}); } catch { /* extension reloaded */ }
      }, 300);
    } else {
      hideToolbar();
    }
  }

  document.addEventListener("mouseup", e => {
    if (e.button !== 0 || isInsideUi(e)) return;
    setTimeout(() => handleSelection(e.pageX), 10);
  });

  // Keyboard selection (Shift + arrows, Ctrl+A)
  document.addEventListener("keyup", e => {
    if (isInsideUi(e)) return;
    if (e.key === "Shift" || e.shiftKey || ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "a")) {
      setTimeout(() => handleSelection(), 10);
    }
  });

  // Hide the toolbar once the selection is gone
  let selectionCheck = null;
  document.addEventListener("selectionchange", () => {
    if (!toolbar) return;
    clearTimeout(selectionCheck);
    selectionCheck = setTimeout(() => {
      if (toolbar && !window.getSelection().toString().trim()) hideToolbar();
    }, 120);
  });

  document.addEventListener("mousedown", e => {
    if (!isInsideUi(e)) hideToolbar();
  }, true);

  document.addEventListener("keydown", e => {
    if (e.key !== "Escape") return;
    if (card) closeCard();
    else hideToolbar();
  });

  // Re-anchor rather than hide: resizes also happen when scrollbars appear.
  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (toolbar) {
        const text = window.getSelection().toString().trim();
        if (text.length > MIN_SELECTION) showToolbar(text);
        else hideToolbar();
      }
      placeCard();
    }, 100);
  });

  // Right-click "TruthScan with TruvantaAI" and Ctrl+Shift+U open the card in place.
  try {
    chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
      if (msg?.type !== "TRUVANTA_CHECK") return false;
      const text = (msg.text || window.getSelection().toString()).trim();
      if (!text) {
        sendResponse({ ok: false });
        return false;
      }
      const from = toolbarBox();
      hideToolbar();
      openCard(text, { from });
      sendResponse({ ok: true });
      return false;
    });
  } catch { /* not running as an extension */ }
})();
