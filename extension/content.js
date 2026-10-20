// Copyright 2027 Bodapati Bharat Chandra. All rights reserved.
// Licensed under the Apache License, Version 2.0
// SPDX-License-Identifier: Apache-2.0
// Project: TruvantaAI - https://github.com/BharatChandra-sys/fake-news-extension
(() => {
  console.log("[TruvantaAI] Content script v2.6.2 loaded");
  
  // Clean up any old tooltips from previous versions
  const oldTooltip = document.getElementById("__Truvanta_tooltip__");
  if (oldTooltip) oldTooltip.remove();
  
  let tooltip = null;
  let floatingToolbar = null;
  let quickActionPopup = null;
  let hideTimer = null;

  // ══════════════════════════════════════════════════════════
  // 🎨 Arc-style Floating Toolbar (like Sider) - COMPACT
  // ══════════════════════════════════════════════════════════
  function createFloatingToolbar() {
    const toolbar = document.createElement("div");
    toolbar.id = "__Truvanta_floating_toolbar__";
    toolbar.innerHTML = `
      <button data-action="truthscan" title="Truth Scan" aria-label="Truth Scan" class="truthscan-btn">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <circle cx="11" cy="11" r="8"/>
          <path d="M21 21l-4.35-4.35"/>
        </svg>
      </button>
      <button data-action="copy" title="Copy" aria-label="Copy">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
          <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
        </svg>
      </button>
      <button data-action="highlight" title="Highlight" aria-label="Highlight">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M9 11l-6 6v3h9l3-3"/>
          <path d="M22 2L11 13"/>
        </svg>
      </button>
      <button data-action="note" title="Add Note" aria-label="Add Note">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
          <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8"/>
        </svg>
      </button>
      <div class="divider"></div>
      <button data-action="more" title="More" aria-label="More options">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="1"/><circle cx="12" cy="5" r="1"/><circle cx="12" cy="19" r="1"/>
        </svg>
      </button>
      <button data-action="close" title="Close" aria-label="Close">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    `;
    
    Object.assign(toolbar.style, {
      position: "fixed",
      zIndex: "2147483647",
      display: "flex",
      alignItems: "center",
      gap: "2px",
      padding: "4px",
      background: "rgba(26, 32, 44, 0.96)",
      backdropFilter: "blur(16px)",
      borderRadius: "10px",
      border: "1px solid rgba(192, 193, 255, 0.2)",
      boxShadow: "0 4px 20px rgba(0,0,0,0.5), 0 0 0 1px rgba(192, 193, 255, 0.1)",
      opacity: "0",
      transform: "translateY(-4px) scale(0.95)",
      transition: "opacity 0.2s cubic-bezier(0.4, 0, 0.2, 1), transform 0.2s cubic-bezier(0.4, 0, 0.2, 1)",
      pointerEvents: "all",
    });

    // Style buttons - COMPACT SIZE
    const style = document.createElement("style");
    style.textContent = `
      #__Truvanta_floating_toolbar__ button {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border: none;
        background: transparent;
        color: #e2e8f0;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.12s ease;
        padding: 0;
      }
      #__Truvanta_floating_toolbar__ button:hover {
        background: rgba(192, 193, 255, 0.15);
        transform: scale(1.08);
      }
      #__Truvanta_floating_toolbar__ button:active {
        transform: scale(0.92);
      }
      #__Truvanta_floating_toolbar__ .truthscan-btn {
        background: linear-gradient(135deg, #c0c1ff 0%, #a8a9ff 100%);
        color: #101419;
        box-shadow: 0 2px 8px rgba(192, 193, 255, 0.3);
      }
      #__Truvanta_floating_toolbar__ .truthscan-btn:hover {
        background: linear-gradient(135deg, #a8a9ff 0%, #9091ff 100%);
        box-shadow: 0 3px 12px rgba(192, 193, 255, 0.5);
        transform: scale(1.08);
      }
      #__Truvanta_floating_toolbar__ .divider {
        width: 1px;
        height: 16px;
        background: rgba(255,255,255,0.1);
        margin: 0 1px;
      }
    `;
    document.head.appendChild(style);

    // Event handlers
    toolbar.addEventListener("click", e => {
      const btn = e.target.closest("button");
      if (!btn) return;
      
      const action = btn.dataset.action;
      const selectedText = window.getSelection().toString().trim();

      switch(action) {
        case "truthscan":
          if (selectedText) {
            showQuickActionPopup(selectedText);
          }
          break;
        case "copy":
          if (selectedText) {
            navigator.clipboard.writeText(selectedText);
            showToast("Copied!");
          }
          break;
        case "highlight":
          highlightSelection();
          break;
        case "close":
          removeFloatingToolbar();
          break;
      }
    });

    document.body.appendChild(toolbar);
    return toolbar;
  }

  function showFloatingToolbar(x, y) {
    // Remove any old tooltip first
    removeTooltip();
    
    if (!floatingToolbar) floatingToolbar = createFloatingToolbar();

    const tw = 280;
    const left = Math.min(Math.max(x - tw / 2, 8), window.innerWidth - tw - 8);
    const top = Math.max(y - 54, 8);

    floatingToolbar.style.left = `${left}px`;
    floatingToolbar.style.top = `${top}px`;
    floatingToolbar.style.opacity = "1";
    floatingToolbar.style.transform = "translateY(0) scale(1)";
    
    console.log("[TruvantaAI] Floating toolbar shown at", left, top);
  }

  function removeFloatingToolbar() {
    if (!floatingToolbar) return;
    floatingToolbar.style.opacity = "0";
    floatingToolbar.style.transform = "translateY(-4px) scale(0.95)";
    setTimeout(() => {
      if (floatingToolbar?.parentNode) floatingToolbar.parentNode.removeChild(floatingToolbar);
      floatingToolbar = null;
    }, 200);
  }

  // ══════════════════════════════════════════════════════════
  // 💬 Arc-style Quick Action Popup
  // ══════════════════════════════════════════════════════════
  function createQuickActionPopup(text) {
    const popup = document.createElement("div");
    popup.id = "__Truvanta_quick_popup__";
    popup.innerHTML = `
      <div class="popup-content">
        <div class="popup-header">
          <div class="ai-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7h1a1 1 0 011 1v3a1 1 0 01-1 1h-1v1a2 2 0 01-2 2H5a2 2 0 01-2-2v-1H2a1 1 0 01-1-1v-3a1 1 0 011-1h1a7 7 0 017-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 012-2z"/>
            </svg>
          </div>
          <span>Ask AI with the above content</span>
        </div>
        <div class="selected-preview">${text.substring(0, 100)}${text.length > 100 ? '...' : ''}</div>
        <button class="action-btn">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7v7c0 5.5 3.8 10.7 10 12 6.2-1.3 10-6.5 10-12V7l-10-5z"/>
            <path d="M9 12l2 2 4-4"/>
          </svg>
          Truth Scan
        </button>
      </div>
    `;

    const style = document.createElement("style");
    style.textContent = `
      #__Truvanta_quick_popup__ {
        position: fixed;
        z-index: 2147483646;
        max-width: 380px;
        background: rgba(30, 34, 40, 0.98);
        backdrop-filter: blur(24px);
        border-radius: 12px;
        border: 1px solid rgba(192,193,255,0.15);
        box-shadow: 0 12px 48px rgba(0,0,0,0.7), 0 4px 16px rgba(0,0,0,0.5);
        opacity: 0;
        transform: translateY(-8px) scale(0.96);
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        pointer-events: all;
      }
      #__Truvanta_quick_popup__ .popup-content {
        padding: 16px;
      }
      #__Truvanta_quick_popup__ .popup-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 12px;
        color: #e8eaed;
        font-family: -apple-system, Inter, sans-serif;
        font-size: 13px;
        font-weight: 500;
      }
      #__Truvanta_quick_popup__ .ai-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: 8px;
        background: linear-gradient(135deg, #c0c1ff 0%, #a8a9ff 100%);
        color: #101419;
      }
      #__Truvanta_quick_popup__ .selected-preview {
        padding: 12px;
        margin-bottom: 12px;
        background: rgba(192, 193, 255, 0.05);
        border-radius: 8px;
        color: #9ca3af;
        font-size: 12px;
        line-height: 1.5;
        font-family: -apple-system, Inter, sans-serif;
        max-height: 80px;
        overflow: hidden;
      }
      #__Truvanta_quick_popup__ .action-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        width: 100%;
        padding: 10px 16px;
        border: none;
        border-radius: 8px;
        background: linear-gradient(135deg, #c0c1ff 0%, #a8a9ff 100%);
        color: #101419;
        font-size: 14px;
        font-weight: 600;
        font-family: -apple-system, Inter, sans-serif;
        cursor: pointer;
        transition: all 0.15s ease;
      }
      #__Truvanta_quick_popup__ .action-btn:hover {
        background: linear-gradient(135deg, #a8a9ff 0%, #9091ff 100%);
        box-shadow: 0 4px 16px rgba(192, 193, 255, 0.4);
        transform: translateY(-1px);
      }
      #__Truvanta_quick_popup__ .action-btn:active {
        transform: scale(0.98);
      }
    `;
    document.head.appendChild(style);

    popup.querySelector(".action-btn").addEventListener("click", () => {
      showInlineAIChat(text);
      removeQuickActionPopup();
      removeFloatingToolbar();
    });

    document.body.appendChild(popup);
    return popup;
  }

  function showQuickActionPopup(text) {
    if (quickActionPopup?.parentNode) quickActionPopup.parentNode.removeChild(quickActionPopup);
    
    quickActionPopup = createQuickActionPopup(text);
    
    const selection = window.getSelection();
    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    
    const left = Math.min(Math.max(rect.left, 8), window.innerWidth - 390);
    const top = rect.bottom + 8;

    quickActionPopup.style.left = `${left}px`;
    quickActionPopup.style.top = `${top}px`;
    
    setTimeout(() => {
      quickActionPopup.style.opacity = "1";
      quickActionPopup.style.transform = "translateY(0) scale(1)";
    }, 10);
  }

  function removeQuickActionPopup() {
    if (!quickActionPopup) return;
    quickActionPopup.style.opacity = "0";
    quickActionPopup.style.transform = "translateY(-8px) scale(0.96)";
    setTimeout(() => {
      if (quickActionPopup?.parentNode) quickActionPopup.parentNode.removeChild(quickActionPopup);
      quickActionPopup = null;
    }, 250);
  }

  // ══════════════════════════════════════════════════════════
  // 💬 Inline AI Chat Panel
  // ══════════════════════════════════════════════════════════
  let inlineChat = null;
  let chatMessages = [];

  function createInlineAIChat(context) {
    const chat = document.createElement("div");
    chat.id = "__Truvanta_inline_chat__";
    chat.innerHTML = `
      <div class="chat-header">
        <div class="chat-branding">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2a2 2 0 012 2c0 .74-.4 1.39-1 1.73V7h1a7 7 0 017 7h1a1 1 0 011 1v3a1 1 0 01-1 1h-1v1a2 2 0 01-2 2H5a2 2 0 01-2-2v-1H2a1 1 0 01-1-1v-3a1 1 0 011-1h1a7 7 0 017-7h1V5.73c-.6-.34-1-.99-1-1.73a2 2 0 012-2z"/>
          </svg>
          <span class="chat-title">Truvanta<span class="ai-text">AI</span></span>
        </div>
        <button class="chat-close" aria-label="Close chat">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      <div class="chat-context">
        <div class="context-label">Selected context:</div>
        <div class="context-text">${context.substring(0, 150)}${context.length > 150 ? '...' : ''}</div>
      </div>
      <div class="chat-messages" id="__Truvanta_chat_messages__"></div>
      <div class="chat-input-wrapper">
        <input type="text" class="chat-input" placeholder="Ask about this content..." id="__Truvanta_chat_input__" />
        <button class="chat-send" aria-label="Send message">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/>
          </svg>
        </button>
      </div>
    `;

    const style = document.createElement("style");
    style.textContent = `
      #__Truvanta_inline_chat__ {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 420px;
        max-height: 600px;
        display: flex;
        flex-direction: column;
        background: rgba(16, 20, 25, 0.98);
        backdrop-filter: blur(24px);
        border-radius: 16px;
        border: 1px solid rgba(192, 193, 255, 0.2);
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.7), 0 8px 24px rgba(0, 0, 0, 0.5);
        z-index: 2147483645;
        opacity: 0;
        transform: translateY(20px) scale(0.95);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        font-family: -apple-system, Inter, sans-serif;
      }
      #__Truvanta_inline_chat__.visible {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
      #__Truvanta_inline_chat__ .chat-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px;
        border-bottom: 1px solid rgba(192, 193, 255, 0.1);
      }
      #__Truvanta_inline_chat__ .chat-branding {
        display: flex;
        align-items: center;
        gap: 10px;
        color: #c0c1ff;
      }
      #__Truvanta_inline_chat__ .chat-title {
        font-size: 16px;
        font-weight: 600;
        color: #e8eaed;
      }
      #__Truvanta_inline_chat__ .ai-text {
        color: #f59e0b;
      }
      #__Truvanta_inline_chat__ .chat-close {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border: none;
        background: transparent;
        color: #9ca3af;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.15s ease;
      }
      #__Truvanta_inline_chat__ .chat-close:hover {
        background: rgba(192, 193, 255, 0.1);
        color: #e8eaed;
      }
      #__Truvanta_inline_chat__ .chat-context {
        padding: 12px 16px;
        background: rgba(192, 193, 255, 0.05);
        border-bottom: 1px solid rgba(192, 193, 255, 0.1);
      }
      #__Truvanta_inline_chat__ .context-label {
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #c0c1ff;
        margin-bottom: 6px;
        font-weight: 600;
      }
      #__Truvanta_inline_chat__ .context-text {
        font-size: 12px;
        line-height: 1.5;
        color: #9ca3af;
      }
      #__Truvanta_inline_chat__ .chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 16px;
        display: flex;
        flex-direction: column;
        gap: 12px;
        min-height: 200px;
        max-height: 400px;
      }
      #__Truvanta_inline_chat__ .chat-messages:empty::before {
        content: "👋 Ask me anything about the selected content...";
        color: #6b7280;
        font-size: 13px;
        text-align: center;
        padding: 40px 20px;
      }
      #__Truvanta_inline_chat__ .chat-message {
        display: flex;
        flex-direction: column;
        gap: 6px;
        animation: messageSlideIn 0.3s ease;
      }
      @keyframes messageSlideIn {
        from {
          opacity: 0;
          transform: translateY(10px);
        }
        to {
          opacity: 1;
          transform: translateY(0);
        }
      }
      #__Truvanta_inline_chat__ .message-role {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }
      #__Truvanta_inline_chat__ .message-role.user {
        color: #c0c1ff;
      }
      #__Truvanta_inline_chat__ .message-role.assistant {
        color: #f59e0b;
      }
      #__Truvanta_inline_chat__ .message-content {
        padding: 12px;
        border-radius: 10px;
        font-size: 13px;
        line-height: 1.6;
        color: #e8eaed;
      }
      #__Truvanta_inline_chat__ .message-content.user {
        background: rgba(192, 193, 255, 0.15);
        border: 1px solid rgba(192, 193, 255, 0.2);
      }
      #__Truvanta_inline_chat__ .message-content.assistant {
        background: rgba(30, 34, 40, 0.8);
        border: 1px solid rgba(192, 193, 255, 0.1);
      }
      #__Truvanta_inline_chat__ .message-content.loading {
        color: #9ca3af;
        font-style: italic;
      }
      #__Truvanta_inline_chat__ .chat-input-wrapper {
        display: flex;
        gap: 8px;
        padding: 12px 16px;
        border-top: 1px solid rgba(192, 193, 255, 0.1);
      }
      #__Truvanta_inline_chat__ .chat-input {
        flex: 1;
        padding: 10px 14px;
        background: rgba(30, 34, 40, 0.8);
        border: 1px solid rgba(192, 193, 255, 0.2);
        border-radius: 8px;
        color: #e8eaed;
        font-size: 13px;
        font-family: -apple-system, Inter, sans-serif;
        outline: none;
        transition: all 0.15s ease;
      }
      #__Truvanta_inline_chat__ .chat-input:focus {
        border-color: #c0c1ff;
        box-shadow: 0 0 0 3px rgba(192, 193, 255, 0.1);
      }
      #__Truvanta_inline_chat__ .chat-input::placeholder {
        color: #6b7280;
      }
      #__Truvanta_inline_chat__ .chat-send {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        border: none;
        background: linear-gradient(135deg, #c0c1ff 0%, #a8a9ff 100%);
        color: #101419;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.15s ease;
      }
      #__Truvanta_inline_chat__ .chat-send:hover {
        background: linear-gradient(135deg, #a8a9ff 0%, #9091ff 100%);
        box-shadow: 0 4px 16px rgba(192, 193, 255, 0.4);
        transform: translateY(-1px);
      }
      #__Truvanta_inline_chat__ .chat-send:active {
        transform: scale(0.95);
      }
      #__Truvanta_inline_chat__ .chat-send:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
    `;
    document.head.appendChild(style);

    // Event handlers
    chat.querySelector(".chat-close").addEventListener("click", removeInlineAIChat);
    
    const input = chat.querySelector(".chat-input");
    const sendBtn = chat.querySelector(".chat-send");
    
    const handleSend = async () => {
      const message = input.value.trim();
      if (!message) return;
      
      // Add user message
      addChatMessage("user", message);
      input.value = "";
      sendBtn.disabled = true;
      
      // Add loading message
      const loadingId = addChatMessage("assistant", "Analyzing...", true);
      
      try {
        console.log("[TruvantaAI Content] Sending chat message:", message.substring(0, 50));
        
        // Get API endpoint - use production URL directly
        const API_URL = localStorage.getItem("FORCE_LOCAL_DEV") === "true"
          ? "http://localhost:8000"
          : "https://factcheckai-gjrk.onrender.com";
        
        console.log("[TruvantaAI Content] Using API URL:", API_URL);
        
        // Get auth token - FIXED: await was missing proper handling
        const storageResult = await chrome.storage.local.get("token");
        const token = storageResult.token;
        console.log("[TruvantaAI Content] Auth token:", token ? "Found ✓" : "Missing ✗");
        
        // Create abort controller for timeout
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 45000); // 45s timeout
        
        try {
          // Call message API with context
          const response = await fetch(`${API_URL}/message`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(token && { "Authorization": `Bearer ${token}` })
            },
            body: JSON.stringify({
              message: message,
              history: [{ role: "user", content: context }],
              session_id: null
            }),
            signal: controller.signal
          });
          
          clearTimeout(timeoutId);
          
          console.log("[TruvantaAI Content] API response status:", response.status);
          
          if (!response.ok) {
            if (response.status === 401) {
              throw new Error("Authentication required. Please log in to the extension.");
            } else if (response.status === 429) {
              throw new Error("Too many requests. Please wait a moment and try again.");
            }
            throw new Error(`API error: ${response.status}`);
          }
          
          const data = await response.json();
          console.log("[TruvantaAI Content] API response:", data.is_claim ? "Claim detected" : "Chat reply");
        
        clearTimeout(timeoutId);
        
        // Remove loading message
        removeChatMessage(loadingId);
        
        // Handle both claim and non-claim responses
        if (data.is_claim) {
          // This is a fact-check claim - show verdict
          const verdict = (data.verdict || "uncertain").toUpperCase();
          const confidence = Math.round((data.confidence || 0) * 100);
          const verdictEmoji = data.verdict === "fake" ? "❌" : data.verdict === "real" ? "✅" : "⚠️";
          
          let replyText = `${verdictEmoji} **${verdict}** (${confidence}% confidence)\n\n`;
          
          if (data.explanation) {
            replyText += `${data.explanation}\n\n`;
          }
          
          if (data.evidence_articles && data.evidence_articles.length > 0) {
            replyText += `**Sources:**\n`;
            data.evidence_articles.slice(0, 3).forEach((article, i) => {
              replyText += `${i + 1}. ${article.title || article.url}\n`;
            });
          }
          
          addChatMessage("assistant", replyText);
        } else {
          // Regular chat response
          addChatMessage("assistant", data.reply || "I couldn't process that. Please try again.");
        }
        
      } catch (error) {
        console.error("[TruvantaAI Content] Chat error:", error);
        removeChatMessage(loadingId);
        
        // Better error messages based on error type
        let errorMessage = "Sorry, I'm having trouble connecting. ";
        
        if (error.name === 'AbortError') {
          errorMessage = "Request timed out. The AI is taking longer than expected. Please try again.";
        } else if (error.message.includes("Authentication")) {
          errorMessage = error.message + "\n\nClick the extension icon to log in.";
        } else if (error.message.includes("Too many requests")) {
          errorMessage = error.message;
        } else if (error.message.includes("NetworkError") || error.message.includes("Failed to fetch")) {
          errorMessage = "Network error. Please check your internet connection and try again.";
        } else {
          errorMessage += "Please try again later.";
        }
        
        addChatMessage("assistant", errorMessage);
      } finally {
        sendBtn.disabled = false;
        input.focus();
      }
    };
    
    sendBtn.addEventListener("click", handleSend);
    input.addEventListener("keypress", (e) => {
      if (e.key === "Enter") handleSend();
    });

    document.body.appendChild(chat);
    return chat;
  }

  function showInlineAIChat(context) {
    if (inlineChat?.parentNode) {
      inlineChat.parentNode.removeChild(inlineChat);
    }
    
    chatMessages = [];
    inlineChat = createInlineAIChat(context);
    
    // Animate in
    setTimeout(() => {
      inlineChat.classList.add("visible");
      inlineChat.querySelector(".chat-input").focus();
    }, 10);
    
    console.log("[TruvantaAI] Inline chat opened");
  }

  function removeInlineAIChat() {
    if (!inlineChat) return;
    inlineChat.classList.remove("visible");
    setTimeout(() => {
      if (inlineChat?.parentNode) {
        inlineChat.parentNode.removeChild(inlineChat);
      }
      inlineChat = null;
      chatMessages = [];
    }, 300);
  }

  function addChatMessage(role, content, isLoading = false) {
    const messagesContainer = document.getElementById("__Truvanta_chat_messages__");
    if (!messagesContainer) return;
    
    const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const messageDiv = document.createElement("div");
    messageDiv.className = "chat-message";
    messageDiv.id = messageId;
    messageDiv.innerHTML = `
      <div class="message-role ${role}">${role === "user" ? "You" : "TruvantaAI"}</div>
      <div class="message-content ${role} ${isLoading ? 'loading' : ''}">${content.replace(/\n/g, '<br>')}</div>
    `;
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    chatMessages.push({ id: messageId, role, content });
    return messageId;
  }

  function removeChatMessage(messageId) {
    const messageEl = document.getElementById(messageId);
    if (messageEl) {
      messageEl.remove();
      chatMessages = chatMessages.filter(m => m.id !== messageId);
    }
  }

  // ══════════════════════════════════════════════════════════
  // 🛠️ Helper Functions
  // ══════════════════════════════════════════════════════════
  function showToast(message) {
    const toast = document.createElement("div");
    toast.textContent = message;
    Object.assign(toast.style, {
      position: "fixed",
      top: "20px",
      left: "50%",
      transform: "translateX(-50%)",
      zIndex: "2147483647",
      padding: "10px 20px",
      background: "rgba(30, 34, 40, 0.95)",
      color: "#e8eaed",
      borderRadius: "8px",
      fontSize: "13px",
      fontFamily: "-apple-system, Inter, sans-serif",
      boxShadow: "0 4px 16px rgba(0,0,0,0.5)",
    });
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2000);
  }

  function highlightSelection() {
    const selection = window.getSelection();
    if (selection.rangeCount > 0) {
      const range = selection.getRangeAt(0);
      const span = document.createElement("span");
      span.style.backgroundColor = "rgba(167, 139, 250, 0.3)";
      span.style.borderRadius = "2px";
      range.surroundContents(span);
      showToast("Highlighted!");
    }
  }

  // ══════════════════════════════════════════════════════════
  // 📌 Original Tooltip (kept for compatibility)
  // ══════════════════════════════════════════════════════════
  function createTooltip() {
    const el = document.createElement("div");
    el.id = "__Truvanta_tooltip__";
    el.innerHTML = `
      <span style="font-size:13px;line-height:1;">🔍</span>
      <span style="font-size:12px;font-weight:600;letter-spacing:0.01em;">TruthScan this</span>
    `;
    Object.assign(el.style, {
      position:        "fixed",
      zIndex:          "2147483647",
      display:         "flex",
      alignItems:      "center",
      gap:             "6px",
      padding:         "7px 12px",
      background:      "#1e2228",
      color:           "#e8eaed",
      borderRadius:    "8px",
      border:          "1px solid rgba(192,193,255,0.18)",
      boxShadow:       "0 4px 16px rgba(0,0,0,0.5)",
      cursor:          "pointer",
      fontFamily:      "-apple-system, 'Inter', sans-serif",
      userSelect:      "none",
      pointerEvents:   "all",
      opacity:         "0",
      transform:       "translateY(4px)",
      transition:      "opacity 0.15s ease, transform 0.15s ease",
      whiteSpace:      "nowrap",
    });

    el.addEventListener("mouseenter", () => clearTimeout(hideTimer));
    el.addEventListener("mouseleave", () => scheduleHide(800));
    el.addEventListener("mousedown", e => {
      e.preventDefault();
      e.stopPropagation();
      const text = window.getSelection().toString().trim();
      if (text) {
        chrome.storage.local.set({ selectedText: text, pendingAnalysis: true }, () => {
          chrome.runtime.sendMessage({ type: "OPEN_POPUP_WITH_TEXT", text });
        });
      }
      removeTooltip();
    });

    document.body.appendChild(el);
    return el;
  }

  function showTooltip(x, y) {
    if (!tooltip) tooltip = createTooltip();

    // Position above the selection, centered
    const tw = 160;
    const left = Math.min(Math.max(x - tw / 2, 8), window.innerWidth - tw - 8);
    const top  = Math.max(y - 44, 8);

    tooltip.style.left    = `${left}px`;
    tooltip.style.top     = `${top}px`;
    tooltip.style.opacity = "1";
    tooltip.style.transform = "translateY(0)";
  }

  function removeTooltip() {
    if (!tooltip) return;
    tooltip.style.opacity   = "0";
    tooltip.style.transform = "translateY(4px)";
    setTimeout(() => {
      if (tooltip && tooltip.parentNode) tooltip.parentNode.removeChild(tooltip);
      tooltip = null;
    }, 150);
  }

  function scheduleHide(delay = 300) {
    clearTimeout(hideTimer);
    hideTimer = setTimeout(() => {
      removeTooltip();
      removeFloatingToolbar();
      removeQuickActionPopup();
    }, delay);
  }

  // Debounce timer for TEXT_SELECTED messages — prevents firing on every
  // character of a drag selection (fires once, 300ms after mouseup settles)
  let _selectionDebounceTimer = null;

  // ══════════════════════════════════════════════════════════
  // 🎯 Event Listeners
  // ══════════════════════════════════════════════════════════
  
  // Listen for mouseup to detect selection
  document.addEventListener("mouseup", e => {
    // Small delay so selection is finalised
    setTimeout(() => {
      const selected = window.getSelection().toString().trim();

      if (selected.length > 20) {
        clearTimeout(hideTimer);
        // Show floating toolbar instead of simple tooltip
        showFloatingToolbar(e.clientX, e.clientY);

        // Debounced background notification — avoids flooding service worker
        clearTimeout(_selectionDebounceTimer);
        _selectionDebounceTimer = setTimeout(() => {
          chrome.runtime.sendMessage({
            type: "TEXT_SELECTED",
            payload: selected
          }).catch(() => {});
        }, 300);
      } else {
        scheduleHide(100);
      }
    }, 10);
  });

  // Hide on click elsewhere
  document.addEventListener("mousedown", e => {
    if (floatingToolbar && !floatingToolbar.contains(e.target) &&
        quickActionPopup && !quickActionPopup.contains(e.target)) {
      scheduleHide(100);
    }
  });

  // Hide on scroll
  document.addEventListener("scroll", () => scheduleHide(100), { passive: true });

})();
