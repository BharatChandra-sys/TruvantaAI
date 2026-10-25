// Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
// Licensed under the Apache License, Version 2.0
// SPDX-License-Identifier: Apache-2.0
// Project: TruvantaAI � https://github.com/BharatChandra-sys/fake-news-extension
/**
 * TruvantaAI — Background Service Worker (Manifest V3)
 *
 * Responsibilities:
 *  - Keep backend alive (alarm-based ping every 4 min)
 *  - Context menu: "TruthScan this" on selected text
 *  - Keyboard shortcuts:
 *      Ctrl+Shift+Y  — open popup
 *      Ctrl+Shift+U  — fact-check selected text
 *      Ctrl+Shift+L  — fact-check visible page text
 *  - Message relay from content script
 */

// ── Backend URL: shared with the popup pages via env.js ───────────────────────
importScripts("../env.js");
let API_BASE = TRUVANTA_API;
// Chrome may stop an extension worker whose fetch runs past 30s, so give up first.
const API_TIMEOUT_MS = 28000;

// ── Keep-alive ────────────────────────────────────────────────────────────────
function pingBackend() {
  fetch(`${API_BASE}/health`, { method: "HEAD" }).catch(() => {});
}

// ── Install / update ──────────────────────────────────────────────────────────
chrome.runtime.onInstalled.addListener(({ reason }) => {
  // Context menu
  chrome.contextMenus.create({
    id:       "analyze-fake-news",
    title:    "TruthScan with TruvantaAI",
    contexts: ["selection"],
  });

  // Alarm-based keep-alive (MV3 service workers can be suspended;
  // setInterval is unreliable — alarms survive suspension)
  chrome.alarms.create("keepAlive", { periodInMinutes: 4 });

  // Ping immediately on install/update
  pingBackend();

  if (reason === "install") {
    // Show a one-time welcome notification
    chrome.notifications.create("Truvanta-welcome", {
      type:    "basic",
      iconUrl: chrome.runtime.getURL("icons/icon128.png"),
      title:   "TruvantaAI installed",
      message: "Press Ctrl+Shift+Y to open, or right-click any text to fact-check.",
    });
  }
});

// ── Alarm handler ─────────────────────────────────────────────────────────────
chrome.alarms.onAlarm.addListener(({ name }) => {
  if (name === "keepAlive") pingBackend();
});

// ── Shared helpers ────────────────────────────────────────────────────────────

/**
 * Open the TruvantaAI popup window anchored to the top-right of the current window.
 */
function openAnalysisPopup() {
  chrome.windows.getCurrent((win) => {
    const width  = 440;
    const height = 640;
    const left   = Math.max(0, (win.left + win.width) - width - 20);
    const top    = win.top + 60;
    chrome.windows.create({
      url:     chrome.runtime.getURL("popup/popup.html"),
      type:    "popup",
      width, height, left, top,
      focused: true,
    });
  });
}

/**
 * Store text in local storage and open the popup.
 * The popup reads selectedText + pendingAnalysis on load and auto-sends.
 */
function openPopupWithText(text) {
  const safeText = (text || "").trim();
  chrome.storage.local.set(
    { selectedText: safeText, pendingAnalysis: !!safeText },
    openAnalysisPopup
  );
}

/**
 * Get the currently selected text from a tab via scripting injection.
 */
async function getSelectedTextFromPage(tabId) {
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId },
      func:   () => (window.getSelection()?.toString() ?? "").trim(),
    });
    return results?.[0]?.result || "";
  } catch {
    return "";
  }
}

/**
 * Get the main visible text from a tab (article > main > body, max 1200 chars).
 */
async function getVisiblePageText(tabId) {
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId },
      func: () => {
        const el = document.querySelector("article, main, [role='main']") || document.body;
        return (el?.innerText || "").replace(/\s+/g, " ").trim().slice(0, 1200);
      },
    });
    return results?.[0]?.result || "";
  } catch {
    return "";
  }
}

/**
 * Get the currently active tab in the focused window.
 */
async function getActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs?.[0] ?? null;
}

/**
 * Show a brief notification (used for shortcut feedback when no text found).
 */
function notify(message) {
  chrome.notifications.create({
    type:    "basic",
    iconUrl: chrome.runtime.getURL("icons/icon48.png"),
    title:   "TruvantaAI",
    message,
  });
}

/**
 * Ask the page's content script to show the in-page check card.
 * Resolves false when there is no content script (e.g. chrome:// pages,
 * the Web Store, or tabs opened before the extension was installed).
 */
async function checkInPage(tabId, text) {
  if (!tabId) return false;
  try {
    const res = await chrome.tabs.sendMessage(tabId, { type: "TRUVANTA_CHECK", text });
    return !!res?.ok;
  } catch {
    return false;
  }
}

// ── Context menu ──────────────────────────────────────────────────────────────
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "analyze-fake-news") {
    const text = info.selectionText || "";
    if (!(await checkInPage(tab?.id, text))) openPopupWithText(text);
  }
});

// ── Keyboard shortcuts ────────────────────────────────────────────────────────
chrome.commands.onCommand.addListener(async (command) => {
  // Ctrl+Shift+Y — just open the popup
  if (command === "open-factchecker") {
    openPopupWithText("");
    return;
  }

  const tab = await getActiveTab();

  // Ctrl+Shift+U — fact-check selected text
  if (command === "analyze-selected-text") {
    if (!tab?.id) { openPopupWithText(""); return; }
    const text = await getSelectedTextFromPage(tab.id);
    if (text) {
      if (!(await checkInPage(tab.id, text))) openPopupWithText(text);
    } else {
      notify("No text selected. Select some text on the page first.");
      openPopupWithText("");
    }
    return;
  }

  // Ctrl+Shift+L — fact-check visible page text
  if (command === "analyze-current-page") {
    if (!tab?.id) { openPopupWithText(""); return; }
    const text = await getVisiblePageText(tab.id);
    if (text) {
      openPopupWithText(text);
    } else {
      notify("Could not extract text from this page.");
      openPopupWithText("");
    }
  }
});

/**
 * Make a backend request on behalf of the in-page card. Content scripts
 * can't call the backend directly: their requests carry the website's
 * origin, which the backend's CORS policy (rightly) rejects.
 */
async function proxyApi({ path, method = "POST", body }) {
  if (typeof path !== "string" || !path.startsWith("/")) return { ok: false, error: "bad_request" };
  const { token } = await chrome.storage.local.get("token");
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        "X-Client": "extension-content",
        "X-Client-Version": chrome.runtime.getManifest().version,
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
    let data = null;
    try { data = await res.json(); } catch { /* empty or non-JSON body */ }
    return { ok: res.ok, status: res.status, data };
  } catch (err) {
    return { ok: false, error: err.name === "AbortError" ? "timeout" : "network" };
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Real-time check for the in-page card. The card opens a port, sends the
 * claim, and receives each Server-Sent Event from /check/stream as it
 * arrives (sources, an early fact-check match, then the verdict).
 * Closing the card disconnects the port, which cancels the request.
 */
const STREAM_IDLE_MS = 25000;  // no bytes for this long → give up (Chrome's limit is 30s)

chrome.runtime.onConnect.addListener((port) => {
  if (port.name !== "truvanta-check") return;
  const controller = new AbortController();
  let open = true;
  let idleTimer = null;
  const send = (msg) => { if (open) { try { port.postMessage(msg); } catch { open = false; } } };
  const resetIdle = () => {
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => { send({ event: "network_error", reason: "timeout" }); controller.abort(); }, STREAM_IDLE_MS);
  };
  port.onDisconnect.addListener(() => { open = false; clearTimeout(idleTimer); controller.abort(); });

  port.onMessage.addListener(async (msg) => {
    if (msg?.type !== "START" || typeof msg.text !== "string") return;
    resetIdle();
    try {
      const { token } = await chrome.storage.local.get("token");
      const res = await fetch(`${API_BASE}/check/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "text/event-stream",
          "X-Client": "extension-content",
          "X-Client-Version": chrome.runtime.getManifest().version,
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ message: msg.text, check: true }),
        signal: controller.signal,
      });
      if (!res.ok || !res.body) {
        send({ event: "http_error", status: res.status });
        return;
      }
      const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
      let buffer = "";
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        resetIdle();
        buffer += value.replace(/\r\n/g, "\n");
        let split;
        while ((split = buffer.indexOf("\n\n")) >= 0) {
          const block = buffer.slice(0, split);
          buffer = buffer.slice(split + 2);
          let event = "message";
          const data = [];
          for (const line of block.split("\n")) {
            if (line.startsWith("event:")) event = line.slice(6).trim();
            else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
          }
          if (!data.length) continue;
          try { send({ event, data: JSON.parse(data.join("\n")) }); } catch { /* malformed event */ }
        }
      }
      send({ event: "end" });
    } catch (err) {
      if (err.name !== "AbortError") send({ event: "network_error", reason: "network" });
    } finally {
      clearTimeout(idleTimer);
    }
  });
});

// ── Messages from content script / popup ─────────────────────────────────────
chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  switch (message.type) {
    case "TEXT_SELECTED":
      chrome.storage.local.set({ selectedText: message.payload || "" });
      return false;  // no async sendResponse needed

    case "OPEN_POPUP_WITH_TEXT":
      openPopupWithText(message.text || "");
      return false;

    case "PING_BACKEND":
      pingBackend();
      return false;

    case "OPEN_LOGIN":
      // The popup's login page; after signing in it continues to the main popup.
      chrome.windows.create({
        url: chrome.runtime.getURL("popup/login.html"),
        type: "popup", width: 420, height: 640, focused: true,
      });
      return false;

    case "TRUVANTA_API":
      proxyApi(message).then(sendResponse);
      return true;  // async sendResponse — keeps the worker alive until it answers

    case "GET_API_BASE":
      sendResponse({ apiBase: API_BASE });
      return true;  // async sendResponse — keep channel open

    case "SET_API_BASE":
      // Runtime override for this session only; env.js stays the default.
      if (message.apiBase) API_BASE = message.apiBase;
      return false;
  }
  return false;
});
