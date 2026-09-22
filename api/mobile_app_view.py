from __future__ import annotations

import json


def render_mobile_app() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#f7f4ed">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <meta name="apple-mobile-web-app-title" content="Health">
  <link rel="manifest" href="/app/manifest.webmanifest">
  <link rel="apple-touch-icon" href="/app/icon.svg">
  <title>Health</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f4ed;
      --panel: #fffdf8;
      --panel-strong: #ffffff;
      --ink: #171915;
      --muted: #666b61;
      --line: #d9d4c8;
      --green: #1f7a4d;
      --amber: #a76500;
      --coral: #c74032;
      --blue: #2369a5;
      --shadow: 0 12px 30px rgba(32, 27, 19, .08);
      --radius: 8px;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; min-height: 100%; background: var(--bg); color: var(--ink); }
    body { -webkit-font-smoothing: antialiased; }
    button, input, textarea { font: inherit; }
    button { touch-action: manipulation; }
    .app { min-height: 100vh; padding: env(safe-area-inset-top) 14px calc(78px + env(safe-area-inset-bottom)); }
    .topbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 2px 12px; position: sticky; top: 0; z-index: 5; background: color-mix(in srgb, var(--bg) 92%, transparent); backdrop-filter: blur(18px); }
    .brand { display: flex; align-items: center; gap: 10px; min-width: 0; }
    .mark { width: 32px; height: 32px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); display: grid; place-items: center; box-shadow: var(--shadow); }
    .brand h1 { margin: 0; font-size: 18px; line-height: 1.05; letter-spacing: 0; }
    .brand p { margin: 1px 0 0; color: var(--muted); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 240px; }
    .icon-button, .primary, .secondary, .chip { min-height: 44px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--panel); color: var(--ink); display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 0 12px; text-decoration: none; }
    .icon-button { width: 44px; padding: 0; }
    .primary { background: var(--ink); color: white; border-color: var(--ink); width: 100%; font-weight: 700; }
    .secondary { background: transparent; }
    .chip { min-height: 36px; font-size: 13px; color: var(--muted); }
    .chip.active { color: white; background: var(--ink); border-color: var(--ink); }
    .content { display: grid; gap: 12px; }
    .panel { background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); padding: 14px; box-shadow: var(--shadow); }
    .hero { background: var(--panel-strong); }
    .row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .stack { display: grid; gap: 10px; }
    .label { color: var(--muted); font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; }
    .phrase { margin: 4px 0 0; font-size: clamp(28px, 12vw, 46px); line-height: .95; letter-spacing: 0; font-weight: 800; }
    .phase { color: var(--muted); font-size: 14px; margin-top: 8px; }
    .dot { width: 13px; height: 13px; border-radius: 999px; background: var(--blue); box-shadow: 0 0 0 6px rgba(35,105,165,.1); flex: 0 0 auto; }
    .tone-green { background: var(--green); box-shadow: 0 0 0 6px rgba(31,122,77,.12); }
    .tone-amber { background: var(--amber); box-shadow: 0 0 0 6px rgba(167,101,0,.13); }
    .tone-coral { background: var(--coral); box-shadow: 0 0 0 6px rgba(199,64,50,.13); }
    .metric { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 10px; align-items: end; }
    .metric strong { font-size: 40px; line-height: .9; letter-spacing: 0; }
    .metric span { color: var(--muted); font-size: 13px; }
    .list { display: grid; gap: 10px; margin: 0; padding: 0; list-style: none; }
    .item { border-top: 1px solid var(--line); padding-top: 10px; display: grid; gap: 3px; }
    .item:first-child { border-top: 0; padding-top: 0; }
    .item-title { font-weight: 750; }
    .item-detail, .small { color: var(--muted); font-size: 13px; line-height: 1.35; }
    .status-pill { font-size: 12px; color: var(--muted); border: 1px solid var(--line); border-radius: 999px; padding: 4px 8px; white-space: nowrap; }
    .tabs { position: fixed; left: 0; right: 0; bottom: 0; padding: 8px 10px calc(8px + env(safe-area-inset-bottom)); background: color-mix(in srgb, var(--bg) 88%, transparent); backdrop-filter: blur(20px); border-top: 1px solid var(--line); display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; z-index: 10; }
    .tab { min-height: 48px; border: 0; background: transparent; border-radius: var(--radius); color: var(--muted); display: grid; place-items: center; gap: 2px; font-size: 11px; }
    .tab svg { width: 20px; height: 20px; }
    .tab.active { background: var(--panel); color: var(--ink); box-shadow: var(--shadow); }
    textarea, input { width: 100%; border: 1px solid var(--line); border-radius: var(--radius); background: white; color: var(--ink); padding: 12px; outline: none; }
    textarea { min-height: 116px; resize: vertical; line-height: 1.35; }
    textarea:focus, input:focus, button:focus-visible, a:focus-visible { outline: 3px solid rgba(35, 105, 165, .22); outline-offset: 2px; }
    .action-grid { display: flex; gap: 8px; overflow-x: auto; padding-bottom: 3px; }
    .capture-actions { display: grid; gap: 10px; }
    .context-box { white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 12px; line-height: 1.45; max-height: 54vh; overflow: auto; }
    .empty { color: var(--muted); border: 1px dashed var(--line); border-radius: var(--radius); padding: 16px; text-align: center; }
    .toast { position: fixed; left: 14px; right: 14px; bottom: calc(74px + env(safe-area-inset-bottom)); background: var(--ink); color: white; border-radius: var(--radius); padding: 12px 14px; box-shadow: var(--shadow); opacity: 0; visibility: hidden; transform: translateY(140%); transition: transform .2s ease, opacity .2s ease, visibility .2s ease; z-index: 20; }
    .toast.show { opacity: 1; visibility: visible; transform: translateY(0); }
    .sheet { position: fixed; inset: 0; display: none; align-items: end; background: rgba(23,25,21,.36); z-index: 30; }
    .sheet.show { display: flex; }
    .sheet-panel { width: 100%; background: var(--panel); border-radius: 16px 16px 0 0; border: 1px solid var(--line); padding: 16px 14px calc(18px + env(safe-area-inset-bottom)); box-shadow: 0 -18px 50px rgba(0,0,0,.18); }
    .sheet-panel h2 { margin: 0 0 4px; font-size: 20px; }
    .sheet-panel p { margin: 0 0 14px; color: var(--muted); font-size: 13px; }
    .locked { display: none; }
    .loading .locked { display: block; }
    @media (min-width: 760px) {
      .app { max-width: 760px; margin: 0 auto; }
      .tabs { left: 50%; right: auto; width: 760px; transform: translateX(-50%); border-left: 1px solid var(--line); border-right: 1px solid var(--line); }
      .grid-two { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    }
    @media (prefers-reduced-motion: reduce) { * { transition: none !important; scroll-behavior: auto !important; } }
  </style>
</head>
<body>
  <main class="app" id="app">
    <header class="topbar">
      <div class="brand">
        <div class="mark" aria-hidden="true"><svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M7 13.2 10.1 16 17 7" stroke="#171915" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
        <div><h1>Health</h1><p id="phaseLine">Loading current phase</p></div>
      </div>
      <button class="icon-button" id="refreshButton" aria-label="Refresh"><svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M20 12a8 8 0 1 1-2.3-5.6M20 4v5h-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg></button>
    </header>
    <section class="content" id="screen"></section>
  </main>
  <nav class="tabs" aria-label="Health app sections">
    <button class="tab active" data-tab="today"><svg viewBox="0 0 24 24" fill="none"><path d="m8 12 3 3 5-7" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2"/></svg><span>Today</span></button>
    <button class="tab" data-tab="capture"><svg viewBox="0 0 24 24" fill="none"><path d="M12 3v10M8 7v4a4 4 0 0 0 8 0V7M5 11a7 7 0 0 0 14 0M12 18v3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg><span>Capture</span></button>
    <button class="tab" data-tab="context"><svg viewBox="0 0 24 24" fill="none"><path d="M7 7h10M7 12h7M7 17h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><rect x="4" y="3" width="16" height="18" rx="2" stroke="currentColor" stroke-width="2"/></svg><span>Context</span></button>
    <button class="tab" data-tab="more"><svg viewBox="0 0 24 24" fill="none"><path d="M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2ZM19 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2ZM5 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z" stroke="currentColor" stroke-width="2"/></svg><span>More</span></button>
  </nav>
  <div class="toast" id="toast" role="status" aria-live="polite"></div>
  <section class="sheet" id="unlockSheet" aria-hidden="true">
    <form class="sheet-panel" id="unlockForm">
      <h2>Unlock capture</h2>
      <p>Use the health dashboard password or the app token. The session stays on this device.</p>
      <div class="stack">
        <input name="username" autocomplete="username" placeholder="Username" value="chad">
        <input name="password" autocomplete="current-password" type="password" placeholder="Password or app token">
        <button class="primary" type="submit">Unlock</button>
        <button class="secondary" type="button" id="closeUnlock">Not now</button>
      </div>
    </form>
  </section>
<script>
const state = { tab: 'today', today: null, context: '', links: null, selectedIntent: 'event', busy: false };
const screen = document.getElementById('screen');
const phaseLine = document.getElementById('phaseLine');
const toast = document.getElementById('toast');
const unlockSheet = document.getElementById('unlockSheet');
const icon = (name) => '';
function esc(value) { return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function fmt(value, unit = '') { if (value === null || value === undefined || value === '') return 'not available'; const n = Number(value); const rendered = Number.isFinite(n) ? new Intl.NumberFormat(undefined,{maximumFractionDigits:2}).format(n) : String(value); return unit ? `${rendered} ${unit}` : rendered; }
function showToast(message) { toast.textContent = message; toast.classList.add('show'); setTimeout(() => toast.classList.remove('show'), 2600); }
function openUnlock() { unlockSheet.classList.add('show'); unlockSheet.setAttribute('aria-hidden', 'false'); }
function closeUnlock() { unlockSheet.classList.remove('show'); unlockSheet.setAttribute('aria-hidden', 'true'); }
async function getJSON(path, options = {}) {
  const res = await fetch(path, { credentials: 'same-origin', ...options });
  if (res.status === 401) { openUnlock(); throw new Error('Unlock required'); }
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}
async function load() {
  try {
    const [today, context] = await Promise.all([getJSON('/api/mobile/today'), getJSON('/api/mobile/context')]);
    state.today = today; state.context = context.markdown || '';
    phaseLine.textContent = today.phase?.title || 'Current phase';
    render();
  } catch (err) {
    if (!state.today) screen.innerHTML = `<div class="panel empty">${esc(err.message)}</div>`;
  }
}
function setTab(tab) {
  state.tab = tab;
  document.querySelectorAll('.tab').forEach(btn => btn.classList.toggle('active', btn.dataset.tab === tab));
  render();
}
function render() {
  if (state.tab === 'today') return renderToday();
  if (state.tab === 'capture') return renderCapture();
  if (state.tab === 'context') return renderContext();
  return renderMore();
}
function renderToday() {
  const t = state.today;
  if (!t) { screen.innerHTML = '<div class="panel empty">Loading</div>'; return; }
  const tone = t.overall?.tone ? `tone-${t.overall.tone}` : '';
  const reminders = (t.not_done_today || []).map(item => `<li class="item"><div class="row"><div class="item-title">${esc(item.title)}</div><span class="status-pill">${esc(item.due)}</span></div><div class="item-detail">${esc(item.detail)}</div></li>`).join('') || '<li class="empty">No open adherence items</li>';
  const tripwire = t.tripwire ? `<section class="panel"><div class="row"><div class="label">Tripwire</div><span class="status-pill">${esc(t.tripwire.state)}</span></div><h3>${esc(t.tripwire.title || 'Review')}</h3><p class="item-detail">${esc(t.tripwire.evidence || '')}</p></section>` : '';
  screen.innerHTML = `
    <section class="panel hero"><div class="row"><div><div class="label">Today</div><div class="phrase">${esc(t.overall?.phrase || t.overall?.state || 'No data')}</div><div class="phase">Day ${esc(t.phase?.day_count ?? 0)} · ${esc(t.phase?.status || 'unknown')}</div></div><span class="dot ${tone}" aria-hidden="true"></span></div></section>
    <section class="panel"><div class="metric"><div><div class="label">${esc(t.progress?.primary_label || 'Progress')}</div><strong>${esc(fmt(t.progress?.primary_value))}</strong><div class="item-detail">Target ${esc(t.progress?.target_label || 'not set')} · ${esc(fmt(t.progress?.rate_value, t.progress?.rate_unit))}</div></div><span>${esc(t.progress?.primary_unit || '')}</span></div></section>
    <section class="panel"><div class="label">Not Done Today</div><ul class="list">${reminders}</ul></section>
    ${tripwire}
    <section class="panel"><div class="label">Next Action</div><h3>${esc(t.next_action?.title || 'No action surfaced')}</h3><p class="item-detail">${esc(t.next_action?.why || '')}</p></section>`;
}
function renderCapture() {
  const t = state.today;
  const actions = t?.capture?.quick_actions || [{ intent: 'event', label: 'Event' }];
  const examples = (t?.capture?.examples || []).map(ex => `<button class="chip" type="button" data-example="${esc(ex)}">${esc(ex)}</button>`).join('');
  const recent = (t?.recent_capture || []).map(item => `<li class="item"><div class="item-title">${esc(item.title)}</div><div class="item-detail">${esc(item.detail)}</div><div class="small">${esc(item.occurred_at)}</div></li>`).join('') || '<li class="empty">No app captures yet</li>';
  screen.innerHTML = `
    <section class="panel"><div class="label">Capture</div><h2>${esc(t?.capture?.primary_prompt || 'What happened today?')}</h2><div class="action-grid">${actions.map(a => `<button class="chip ${state.selectedIntent === a.intent ? 'active' : ''}" data-intent="${esc(a.intent)}" type="button">${esc(a.label)}</button>`).join('')}</div><div class="capture-actions"><textarea id="captureText" placeholder="Type or dictate a note"></textarea><button class="primary" id="submitCapture" type="button">Log</button></div></section>
    <section class="panel"><div class="label">Examples</div><div class="action-grid">${examples}</div></section>
    <section class="panel"><div class="label">Recent</div><ul class="list">${recent}</ul></section>`;
  screen.querySelectorAll('[data-intent]').forEach(btn => btn.addEventListener('click', () => { state.selectedIntent = btn.dataset.intent; renderCapture(); }));
  screen.querySelectorAll('[data-example]').forEach(btn => btn.addEventListener('click', () => { document.getElementById('captureText').value = btn.dataset.example; }));
  document.getElementById('submitCapture').addEventListener('click', submitCapture);
}
async function submitCapture() {
  const text = document.getElementById('captureText').value.trim();
  if (!text) return;
  try {
    const result = await getJSON('/api/mobile/capture', { method: 'POST', headers: {'content-type':'application/json'}, body: JSON.stringify({ intent: state.selectedIntent, text, source: 'pwa', fields: {} }) });
    showToast(result.summary || 'Logged');
    await load();
    setTab('today');
  } catch (err) {
    if (err.message !== 'Unlock required') showToast(err.message);
  }
}
function renderContext() {
  screen.innerHTML = `<section class="panel"><div class="row"><div><div class="label">Context</div><h2>Protocol packet</h2></div><button class="secondary" id="copyContext" type="button">Copy</button></div></section><section class="panel context-box">${esc(state.context || 'Context unavailable.')}</section><section class="panel"><div class="label">Project Links</div><div class="stack"><button class="secondary" id="loadLinks" type="button">Load links</button><div id="linksBox" class="small"></div></div></section>`;
  document.getElementById('copyContext').addEventListener('click', async () => { await navigator.clipboard.writeText(state.context || ''); showToast('Copied'); });
  document.getElementById('loadLinks').addEventListener('click', loadLinks);
}
async function loadLinks() {
  try {
    state.links = await getJSON('/api/mobile/links');
    const links = [];
    if (state.links.claude_project_url) links.push(`<a class="secondary" href="${esc(state.links.claude_project_url)}">Claude</a>`);
    if (state.links.chatgpt_project_url) links.push(`<a class="secondary" href="${esc(state.links.chatgpt_project_url)}">ChatGPT</a>`);
    document.getElementById('linksBox').innerHTML = links.length ? links.join(' ') : 'No project links configured.';
  } catch (err) {
    if (err.message !== 'Unlock required') showToast(err.message);
  }
}
function renderMore() {
  screen.innerHTML = `<section class="panel"><div class="label">Phone App</div><h2>Installable web app</h2><p class="item-detail">Open from the iPhone share sheet with Add to Home Screen for a full-screen app shell.</p></section><section class="panel"><div class="label">Status</div><ul class="list"><li class="item"><div class="item-title">Capture</div><div class="item-detail">${esc(state.today?.capture?.write_status || 'unknown')}</div></li><li class="item"><div class="item-title">Generated</div><div class="item-detail">${esc(state.today?.generated_at || 'unknown')}</div></li></ul></section>`;
}
document.querySelectorAll('.tab').forEach(btn => btn.addEventListener('click', () => setTab(btn.dataset.tab)));
document.getElementById('refreshButton').addEventListener('click', load);
document.getElementById('closeUnlock').addEventListener('click', closeUnlock);
document.getElementById('unlockForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const password = form.get('password');
  const username = form.get('username') || 'chad';
  try {
    await getJSON('/api/mobile/session', { method: 'POST', headers: {'content-type':'application/json'}, body: JSON.stringify({ username, password, token: password }) });
    closeUnlock();
    showToast('Unlocked');
  } catch (err) { showToast('Unlock failed'); }
});
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/app/service-worker.js').catch(() => {});
load();
</script>
</body>
</html>"""


def render_manifest() -> str:
    return json.dumps(
        {
            "name": "Health Companion",
            "short_name": "Health",
            "start_url": "/app",
            "scope": "/",
            "display": "standalone",
            "background_color": "#f7f4ed",
            "theme_color": "#f7f4ed",
            "icons": [
                {"src": "/app/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}
            ],
        },
        separators=(",", ":"),
    )


def render_service_worker() -> str:
    return """const CACHE = 'health-companion-v1';
const ASSETS = ['/app', '/app/manifest.webmanifest', '/app/icon.svg'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(ASSETS)));
  self.skipWaiting();
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key)))));
  self.clients.claim();
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/api/')) return;
  event.respondWith(fetch(event.request).catch(() => caches.match(event.request).then(hit => hit || caches.match('/app'))));
});
"""


def render_icon_svg() -> str:
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="96" fill="#f7f4ed"/>
  <rect x="86" y="86" width="340" height="340" rx="72" fill="#fffdf8" stroke="#171915" stroke-width="18"/>
  <path d="M160 263l67 64 129-151" fill="none" stroke="#1f7a4d" stroke-width="34" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="356" cy="156" r="24" fill="#c74032"/>
</svg>"""
