// Truvanta popup icons: replaces Material-style ligature names with inline SVG.
// Keeps the existing markup (<span class="material-symbols-outlined">name</span>)
// working on every page, with no external icon font. Also upgrades icons that
// scripts add later or retarget by setting textContent.
(function () {
  const S = (d) => d;
  const circle = '<circle cx="12" cy="12" r="8.5"/>';
  const ICONS = {
    warning: S('<path d="M12 4 2.8 20h18.4L12 4Z"/><path d="M12 10v4.5M12 17.4v.1"/>'),
    report: S(circle + '<path d="M12 7.5v5M12 16v.1"/>'),
    error: S(circle + '<path d="M12 7.5v5M12 16v.1"/>'),
    info: S(circle + '<path d="M12 11v5M12 8v.1"/>'),
    history: S('<path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1L3.5 8.5"/><path d="M3.5 4v4.5H8M12 7.5V12l3 2"/>'),
    schedule: S(circle + '<path d="M12 7.5V12l3 2"/>'),
    settings: S('<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>'),
    fact_check: S('<path d="M12 3 4.5 6v5.5c0 4.3 3.1 7.9 7.5 9.5 4.4-1.6 7.5-5.2 7.5-9.5V6L12 3Z"/><path d="m8.8 12 2.4 2.4 4-4.6"/>'),
    verified: S('<path d="M12 3 4.5 6v5.5c0 4.3 3.1 7.9 7.5 9.5 4.4-1.6 7.5-5.2 7.5-9.5V6L12 3Z"/><path d="m8.8 12 2.4 2.4 4-4.6"/>'),
    policy: S('<path d="M12 3 4.5 6v5.5c0 4.3 3.1 7.9 7.5 9.5 4.4-1.6 7.5-5.2 7.5-9.5V6L12 3Z"/><path d="M9 11.5h6M9 14.5h4"/>'),
    arrow_back: S('<path d="M19 12H5M11 6l-6 6 6 6"/>'),
    dashboard: S('<rect x="4" y="4" width="6.5" height="6.5" rx="1.5"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.5"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1.5"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.5"/>'),
    chat: S('<path d="M5 5h14a1.5 1.5 0 0 1 1.5 1.5v8A1.5 1.5 0 0 1 19 16h-7l-4.5 3.5V16H5a1.5 1.5 0 0 1-1.5-1.5v-8A1.5 1.5 0 0 1 5 5Z"/>'),
    trending_up: S('<path d="m3 17 6-6 4 4 8-8M15 7h6v6"/>'),
    check_circle: S(circle + '<path d="m8.5 12.3 2.5 2.5 4.5-5"/>'),
    cancel: S(circle + '<path d="m9 9 6 6M15 9l-6 6"/>'),
    help: S(circle + '<path d="M9.7 9.6a2.4 2.4 0 1 1 3.4 2.2c-.7.4-1.1.9-1.1 1.7M12 16.6v.1"/>'),
    close: S('<path d="M6 6l12 12M18 6 6 18"/>'),
    bookmark: S('<path d="M7 4h10v16l-5-3.5L7 20V4Z"/>'),
    bookmark_add: S('<path d="M7 4h10v16l-5-3.5L7 20V4Z"/><path d="M12 8v4M10 10h4"/>'),
    bookmark_remove: S('<path d="M7 4h10v16l-5-3.5L7 20V4Z"/><path d="M10 10h4"/>'),
    refresh: S('<path d="M20 11a8 8 0 1 0-2.3 6"/><path d="M20 5v6h-6"/>'),
    newspaper: S('<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 9h8M8 13h8M8 16h5"/>'),
    logout: S('<path d="M10 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h4M15 8l4 4-4 4M19 12H9"/>'),
    image: S('<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="m4 18 5-5 4 4 3-3 4.5 4"/>'),
    flag: S('<path d="M6 21V4M6 5h11l-2 3.5L17 12H6"/>'),
    flag_circle: S('<path d="M6 21V4M6 5h11l-2 3.5L17 12H6"/>'),
    delete: S('<path d="M4.5 7h15M10 7V4.5h4V7M6.5 7l.8 12.5h9.4L17.5 7M10 11v5M14 11v5"/>'),
    whatshot: S('<path d="M12 21c-3.6 0-6-2.4-6-5.6 0-3 2.2-4.6 3-7 1.8 1 3 2.6 3.2 4.4 1-.8 1.6-2 1.6-3.4 2.4 2 4.2 4.4 4.2 6.2 0 3.2-2.4 5.4-6 5.4Z"/>'),
    smart_toy: S('<rect x="5" y="8" width="14" height="11" rx="3"/><path d="M12 8V5.5M9.5 13v1M14.5 13v1"/><circle cx="12" cy="4.5" r="1"/>'),
    skip_next: S('<path d="M6 5v14l9-7-9-7ZM18 5v14"/>'),
    send: S('<path d="M12 19V5M6 11l6-6 6 6"/>'),
    picture_as_pdf: S('<path d="M7 3.5h7l4 4V20a.5.5 0 0 1-.5.5h-10.5A.5.5 0 0 1 6.5 20V4a.5.5 0 0 1 .5-.5Z"/><path d="M14 3.5V8h4M9 13h6M9 16.5h6"/>'),
    description: S('<path d="M7 3.5h7l4 4V20a.5.5 0 0 1-.5.5h-10.5A.5.5 0 0 1 6.5 20V4a.5.5 0 0 1 .5-.5Z"/><path d="M14 3.5V8h4M9 13h6M9 16.5h6"/>'),
    percent: S('<path d="M19 5 5 19"/><circle cx="7" cy="7" r="2"/><circle cx="17" cy="17" r="2"/>'),
    open_in_new: S('<path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/>'),
    monitoring: S('<path d="M3 12h4l3-7 4 14 3-7h4"/>'),
    model_training: S('<circle cx="12" cy="12" r="2.5"/><circle cx="5" cy="6" r="1.8"/><circle cx="19" cy="6" r="1.8"/><circle cx="5" cy="18" r="1.8"/><circle cx="19" cy="18" r="1.8"/><path d="m6.5 7.2 3.6 3.3M17.5 7.2l-3.6 3.3M6.5 16.8l3.6-3.3M17.5 16.8l-3.6-3.3"/>'),
    format_list_bulleted: S('<path d="M9 7h11M9 12h11M9 17h11M4.5 7v.1M4.5 12v.1M4.5 17v.1"/>'),
    database: S('<ellipse cx="12" cy="6" rx="7" ry="2.7"/><path d="M5 6v12c0 1.5 3.1 2.7 7 2.7s7-1.2 7-2.7V6M5 12c0 1.5 3.1 2.7 7 2.7s7-1.2 7-2.7"/>'),
    mic: S('<rect x="9" y="3.5" width="6" height="11" rx="3"/><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v3"/>'),
    graphic_eq: S('<path d="M5 10v4M9 6v12M13 9v6M17 4v16M21 11v2"/>'),
    menu: S('<path d="M4 7h16M4 12h16M4 17h16"/>'),
    edit_square: S('<path d="M12 5H6a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-6"/><path d="m18.5 3.5 2 2L12 14l-3 1 1-3 8.5-8.5Z"/>'),
    audiotrack: S('<path d="M9 18V6l10-2v12"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="16.5" cy="16" r="2.5"/>'),
    add_circle: S(circle + '<path d="M12 8.5v7M8.5 12h7"/>'),
    add: S('<path d="M12 5v14M5 12h14"/>'),
    check: S('<path d="m5 12.5 4.5 4.5L19 7"/>'),
    chevron_right: S('<path d="m9 5 7 7-7 7"/>'),
    search: S('<circle cx="11" cy="11" r="6.5"/><path d="m16 16 4.5 4.5"/>'),
  };
  ICONS.grid_view = ICONS.dashboard;
  ICONS.chat_bubble = ICONS.chat;
  ICONS.bookmark_border = ICONS.bookmark;
  ICONS.hub = ICONS.model_training;

  function svg(name) {
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' +
      ICONS[name] + '</svg>';
  }

  function upgrade(el) {
    if (!el || el.nodeType !== 1 || !el.classList.contains('material-symbols-outlined')) return;
    // Only plain text children mean "a name was set"; our own <svg> is left alone.
    if (el.firstElementChild && el.firstElementChild.tagName.toLowerCase() === 'svg' && !el.textContent.trim()) return;
    const name = el.textContent.trim();
    if (!name || !ICONS[name]) return;
    el.dataset.icon = name;
    el.innerHTML = svg(name);
  }

  function scan(root) {
    if (!root || root.nodeType !== 1) return;
    if (root.classList.contains('material-symbols-outlined')) upgrade(root);
    root.querySelectorAll && root.querySelectorAll('.material-symbols-outlined').forEach(upgrade);
  }

  function start() {
    scan(document.body);
    new MutationObserver(function (list) {
      for (const m of list) {
        if (m.type === 'childList') {
          m.addedNodes.forEach(function (n) {
            if (n.nodeType === 1) scan(n);
            else if (n.nodeType === 3 && n.parentElement) upgrade(n.parentElement);
          });
        } else if (m.type === 'characterData' && m.target.parentElement) {
          upgrade(m.target.parentElement);
        }
      }
    }).observe(document.body, { childList: true, subtree: true, characterData: true });
  }

  if (document.body) start(); else document.addEventListener('DOMContentLoaded', start);
  // Flat Truvanta mark (same paths as the in-page card and the website).
  function mark(height) {
    var w = Math.round(height * 40 / 31);
    return '<svg class="tv-mark" width="' + w + '" height="' + height + '" viewBox="0 0 40 31" fill="none" aria-hidden="true" focusable="false">' +
      '<path d="M11.6 9.6V24.6C11.6 27.5 13.2 29.2 16.2 29.2" stroke="#ededef" stroke-width="4"/>' +
      '<path d="M10.4 9.4 19.4 20.6 33.6 7.4" stroke="#0a0a0b" stroke-width="6.6" stroke-linejoin="round"/>' +
      '<path d="M10.4 9.4 19.4 20.6 33.6 7.4" stroke="#ffc53d" stroke-width="4.2" stroke-linejoin="round"/>' +
      '<path d="M0.4 11.4C1.8 5.6 4.6 2.4 9.6 2.4H32.4L26 9.2H10.6C6.4 9.2 3 9.9 0.4 11.4Z" fill="#ededef"/>' +
      '<path d="M0.4 11.4C1.8 5.6 4.6 2.4 9.6 2.4H12.4C8.2 3 5.6 5.4 4.4 9.6 2.8 10 1.4 10.6 0.4 11.4Z" fill="#ffc53d"/>' +
      '<g fill="#ffc53d"><rect x="37.2" y="0.2" width="2.7" height="2.7" rx="0.5"/><rect x="34.2" y="3" width="1.9" height="1.9" rx="0.4"/>' +
      '<rect x="36.3" y="5.8" width="2.1" height="2.1" rx="0.4"/><rect x="34.8" y="10.2" width="2" height="2" rx="0.4" fill-opacity="0.55"/></g></svg>';
  }
  window.TruvantaIcons = { svg: svg, mark: mark, has: function (n) { return !!ICONS[n]; } };
})();
