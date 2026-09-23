from __future__ import annotations

import json


def render_mobile_app() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#f5f2ea">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <meta name="apple-mobile-web-app-title" content="Health">
  <link rel="manifest" href="/app/manifest.webmanifest">
  <link rel="apple-touch-icon" href="/app/icon.svg">
  <title>Health</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5f2ea;
      --surface: #fffdf7;
      --surface-strong: #ffffff;
      --ink: #141814;
      --muted: #687064;
      --soft: #ece7db;
      --line: #d8d1c2;
      --ok: #1f7a4d;
      --warn: #9a6500;
      --bad: #bf4338;
      --blue: #235f92;
      --focus: rgba(35, 95, 146, .24);
      --shadow: 0 10px 28px rgba(31, 28, 22, .08);
      --radius: 8px;
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Segoe UI", sans-serif;
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; width: 100%; height: 100%; background: var(--bg); color: var(--ink); overflow: hidden; }
    body { -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility; }
    button, input, textarea { font: inherit; }
    button { touch-action: manipulation; -webkit-tap-highlight-color: transparent; }
    a { color: inherit; }
    .phone-shell {
      width: min(100vw, 430px);
      height: 100dvh;
      min-height: 100svh;
      margin: 0 auto;
      background: var(--bg);
      display: grid;
      grid-template-rows: auto minmax(0, 1fr) auto;
      position: relative;
      overflow: hidden;
    }
    .topbar {
      padding: calc(10px + env(safe-area-inset-top)) 14px 8px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      align-items: center;
      gap: 10px;
      background: color-mix(in srgb, var(--bg) 94%, transparent);
      backdrop-filter: blur(18px);
      border-bottom: 1px solid rgba(216, 209, 194, .72);
      z-index: 3;
    }
    .brand { min-width: 0; display: flex; align-items: center; gap: 10px; }
    .mark {
      width: 34px;
      height: 34px;
      border-radius: var(--radius);
      border: 1px solid var(--line);
      background: var(--surface-strong);
      display: grid;
      place-items: center;
      flex: 0 0 auto;
      box-shadow: 0 5px 14px rgba(31, 28, 22, .07);
    }
    .brand-text { min-width: 0; }
    .brand h1 { margin: 0; font-size: 18px; line-height: 1.05; letter-spacing: 0; }
    .brand p { margin: 2px 0 0; color: var(--muted); font-size: 12px; line-height: 1.2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .view {
      min-width: 0;
      overflow-y: auto;
      overscroll-behavior: contain;
      -webkit-overflow-scrolling: touch;
      scrollbar-width: none;
      padding: 10px 12px 16px;
      display: grid;
      align-content: start;
      gap: 10px;
    }
    .view::-webkit-scrollbar { display: none; }
    .tabbar {
      padding: 7px 10px calc(7px + env(safe-area-inset-bottom));
      background: color-mix(in srgb, var(--surface) 92%, transparent);
      backdrop-filter: blur(18px);
      border-top: 1px solid var(--line);
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 6px;
      z-index: 4;
    }
    .tab {
      min-width: 0;
      min-height: 50px;
      border: 0;
      border-radius: var(--radius);
      background: transparent;
      color: var(--muted);
      display: grid;
      place-items: center;
      gap: 2px;
      padding: 5px 2px;
      font-size: 11px;
      line-height: 1;
    }
    .tab svg { width: 20px; height: 20px; stroke-width: 2.1; }
    .tab.active { background: var(--ink); color: white; box-shadow: 0 8px 18px rgba(20, 24, 20, .14); }
    .icon-button, .primary, .secondary, .segmented-button {
      min-height: 44px;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--surface-strong);
      color: var(--ink);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 0 12px;
      text-decoration: none;
      font-weight: 700;
    }
    .icon-button { width: 44px; padding: 0; flex: 0 0 auto; }
    .primary { width: 100%; background: var(--ink); color: white; border-color: var(--ink); }
    .secondary { background: transparent; color: var(--ink); }
    .surface {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }
    .section { padding: 12px; }
    .summary { padding: 12px; background: var(--surface-strong); }
    .row { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
    .row-start { display: flex; align-items: center; gap: 9px; min-width: 0; }
    .stack { display: grid; gap: 9px; }
    .kicker { color: var(--muted); font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .06em; line-height: 1.2; }
    .status-pill { color: var(--muted); background: var(--surface-strong); border: 1px solid var(--line); border-radius: 999px; padding: 4px 8px; font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .summary > .row .status-pill { max-width: 58%; }
    .verdict { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 10px; align-items: center; margin-top: 9px; }
    .signal { width: 14px; height: 38px; border-radius: 999px; background: var(--blue); box-shadow: 0 0 0 5px rgba(35, 95, 146, .09); }
    .signal.tone-green { background: var(--ok); box-shadow: 0 0 0 5px rgba(31, 122, 77, .10); }
    .signal.tone-amber { background: var(--warn); box-shadow: 0 0 0 5px rgba(154, 101, 0, .12); }
    .signal.tone-coral { background: var(--bad); box-shadow: 0 0 0 5px rgba(191, 67, 56, .12); }
    .phrase { margin: 0; font-size: 31px; line-height: .98; letter-spacing: 0; font-weight: 850; overflow-wrap: anywhere; }
    .meta { color: var(--muted); font-size: 13px; line-height: 1.35; margin-top: 4px; }
    .stat-strip { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1px; margin-top: 12px; border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; background: var(--line); }
    .stat { min-width: 0; background: #fbf8f0; padding: 9px 8px; }
    .stat b { display: block; font-size: 16px; line-height: 1.1; letter-spacing: 0; overflow-wrap: anywhere; }
    .stat span { display: block; color: var(--muted); font-size: 11px; line-height: 1.2; margin-top: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .section-title { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 8px; }
    .section-title h2, .sheet-panel h2 { margin: 0; font-size: 18px; line-height: 1.1; letter-spacing: 0; }
    .task-list, .plain-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
    .task-row {
      min-width: 0;
      display: grid;
      grid-template-columns: auto minmax(0, 1fr) auto;
      gap: 9px;
      align-items: start;
      padding: 9px 0 0;
      border-top: 1px solid var(--line);
    }
    .task-row:first-child { border-top: 0; padding-top: 0; }
    .check {
      width: 22px;
      height: 22px;
      border: 2px solid var(--ink);
      border-radius: 7px;
      display: grid;
      place-items: center;
      margin-top: 1px;
      color: transparent;
      background: var(--surface-strong);
    }
    .task-title, .item-title { font-weight: 780; line-height: 1.2; overflow-wrap: anywhere; }
    .detail { color: var(--muted); font-size: 13px; line-height: 1.35; margin-top: 3px; }
    .detail.clamp { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
    .banner { padding: 12px; display: grid; grid-template-columns: 4px minmax(0, 1fr); gap: 10px; align-items: stretch; }
    .banner-rule { border-radius: 999px; background: var(--warn); }
    .banner.high .banner-rule { background: var(--bad); }
    .banner h3, .next h3, .capture-card h2 { margin: 2px 0 0; font-size: 17px; line-height: 1.18; letter-spacing: 0; }
    .next { padding: 12px; }
    .small-button { min-height: 36px; padding: 0 10px; border: 1px solid var(--line); border-radius: var(--radius); background: var(--surface-strong); color: var(--ink); font-size: 13px; font-weight: 750; }
    .segmented { display: flex; gap: 7px; overflow-x: auto; padding: 1px 0 3px; scrollbar-width: none; }
    .segmented::-webkit-scrollbar { display: none; }
    .segmented-button { min-height: 38px; white-space: nowrap; font-size: 13px; color: var(--muted); font-weight: 760; }
    .segmented-button.active { background: var(--ink); border-color: var(--ink); color: white; }
    .capture-intents { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); overflow: visible; }
    .capture-intents .segmented-button { min-width: 0; padding: 0 8px; }
    textarea, input {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: var(--radius);
      background: var(--surface-strong);
      color: var(--ink);
      padding: 12px;
      outline: none;
    }
    textarea { min-height: 104px; resize: none; line-height: 1.35; }
    input { min-height: 46px; }
    textarea:focus, input:focus, button:focus-visible, a:focus-visible { outline: 3px solid var(--focus); outline-offset: 2px; }
    .capture-card { padding: 12px; display: grid; gap: 8px; }
    .capture-card textarea { min-height: 92px; }
    .capture-card .primary { min-height: 42px; }
    .quick-drawer { border-top: 1px solid var(--line); padding-top: 8px; }
    .quick-drawer summary { min-height: 34px; display: flex; align-items: center; color: var(--muted); font-size: 13px; font-weight: 760; list-style: none; }
    .quick-drawer summary::-webkit-details-marker { display: none; }
    .quick-note { display: flex; gap: 7px; overflow-x: auto; padding-bottom: 3px; scrollbar-width: none; }
    .quick-note::-webkit-scrollbar { display: none; }
    .body-hero { padding: 12px; background: var(--surface-strong); }
    .scan-value { display: grid; gap: 2px; margin-top: 10px; }
    .scan-value strong { font-size: 45px; line-height: .9; letter-spacing: 0; }
    .scan-value span { color: var(--muted); font-size: 13px; font-weight: 760; }
    .body-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; margin-top: 10px; }
    .body-tile { min-width: 0; border: 1px solid var(--line); border-radius: var(--radius); background: #fbf8f0; padding: 9px; }
    .body-tile b { display: block; font-size: 20px; line-height: 1.05; letter-spacing: 0; overflow-wrap: anywhere; }
    .body-tile span { display: block; margin-top: 4px; color: var(--muted); font-size: 11px; line-height: 1.2; }
    .body-chart { width: 100%; height: 122px; display: block; margin-top: 10px; border: 1px solid var(--line); border-radius: var(--radius); background: #fbf8f0; }
    .chart-grid { stroke: rgba(104,112,100,.22); stroke-width: .5; }
    .chart-axis { stroke: rgba(20,24,20,.34); stroke-width: .9; }
    .chart-line { fill: none; stroke: var(--bad); stroke-width: 2.4; stroke-linecap: round; stroke-linejoin: round; }
    .chart-dot { fill: var(--bad); stroke: var(--surface-strong); stroke-width: 1.6; }
    .chart-label { fill: var(--muted); font-size: 7px; }
    .anchor-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 8px;
      padding: 9px 0 0;
      border-top: 1px solid var(--line);
    }
    .anchor-row:first-child { border-top: 0; padding-top: 0; }
    .anchor-metrics { color: var(--muted); font-size: 12px; line-height: 1.35; margin-top: 3px; }
    .delta-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
    .recent-row, .status-row {
      display: grid;
      gap: 3px;
      padding: 9px 0 0;
      border-top: 1px solid var(--line);
    }
    .recent-row:first-child, .status-row:first-child { border-top: 0; padding-top: 0; }
    .context-box {
      max-height: 58dvh;
      overflow: auto;
      white-space: pre-wrap;
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 12px;
      line-height: 1.45;
      padding: 12px;
    }
    .empty {
      border: 1px dashed var(--line);
      border-radius: var(--radius);
      padding: 13px;
      color: var(--muted);
      text-align: center;
      font-size: 13px;
      line-height: 1.35;
    }
    .toast {
      position: fixed;
      left: max(12px, calc((100vw - 430px) / 2 + 12px));
      right: max(12px, calc((100vw - 430px) / 2 + 12px));
      bottom: calc(76px + env(safe-area-inset-bottom));
      background: var(--ink);
      color: white;
      border-radius: var(--radius);
      padding: 12px 14px;
      box-shadow: 0 16px 38px rgba(20, 24, 20, .24);
      opacity: 0;
      visibility: hidden;
      transform: translateY(120%);
      transition: opacity .18s ease, transform .18s ease, visibility .18s ease;
      z-index: 20;
      font-size: 14px;
    }
    .toast.show { opacity: 1; visibility: visible; transform: translateY(0); }
    .sheet { position: fixed; inset: 0; display: none; align-items: end; justify-content: center; background: rgba(20, 24, 20, .34); z-index: 30; }
    .sheet.show { display: flex; }
    .sheet-panel {
      width: min(100vw, 430px);
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 16px 16px 0 0;
      padding: 16px 14px calc(18px + env(safe-area-inset-bottom));
      box-shadow: 0 -18px 48px rgba(20, 24, 20, .2);
    }
    .sheet-panel p { margin: 5px 0 13px; color: var(--muted); font-size: 13px; line-height: 1.35; }
    .loading-line { height: 12px; border-radius: 999px; background: linear-gradient(90deg, var(--soft), #fbf8f0, var(--soft)); background-size: 200% 100%; animation: load 1.2s infinite linear; }
    @keyframes load { to { background-position: -200% 0; } }
    @media (min-width: 560px) {
      body { background: #e8e2d5; }
      .phone-shell { border-left: 1px solid var(--line); border-right: 1px solid var(--line); }
    }
    @media (max-width: 360px) {
      .phrase { font-size: 27px; }
      .stat b { font-size: 15px; }
      .tab { font-size: 10px; }
    }
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { animation-duration: .01ms !important; animation-iteration-count: 1 !important; transition-duration: .01ms !important; scroll-behavior: auto !important; }
    }
  </style>
</head>
<body>
  <div class="phone-shell" id="appShell">
    <header class="topbar">
      <div class="brand">
        <div class="mark" aria-hidden="true"><svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M7 13.2 10.2 16 17.5 7" stroke="#141814" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"></path></svg></div>
        <div class="brand-text"><h1>Health</h1><p id="phaseLine">Syncing current phase</p></div>
      </div>
      <button class="icon-button" id="refreshButton" type="button" aria-label="Refresh health data"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M20 12a8 8 0 1 1-2.35-5.66M20 4v5h-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path></svg></button>
    </header>

    <main class="view" id="screen" tabindex="-1" aria-live="polite"></main>

    <nav class="tabbar" aria-label="Health app sections">
      <button class="tab active" type="button" data-tab="today" aria-label="Today"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="9" stroke="currentColor"></circle><path d="m8 12 2.6 2.6L16.5 8" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"></path></svg><span>Today</span></button>
      <button class="tab" type="button" data-tab="body" aria-label="Body composition"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3v18M7 6.5c0 2.4 2.2 4 5 4s5-1.6 5-4M6.5 14.5c1.5 1.8 3.2 2.7 5.5 2.7s4-.9 5.5-2.7" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"></path><path d="M8 6.5a4 4 0 0 1 8 0M7 14.5a5 5 0 0 1 10 0" stroke="currentColor" stroke-linecap="round"></path></svg><span>Body</span></button>
      <button class="tab" type="button" data-tab="capture" aria-label="Capture"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3v10M8 7v4a4 4 0 0 0 8 0V7M5 11a7 7 0 0 0 14 0M12 18v3" stroke="currentColor" stroke-linecap="round"></path></svg><span>Capture</span></button>
      <button class="tab" type="button" data-tab="context" aria-label="Context"><svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><rect x="4" y="3" width="16" height="18" rx="2" stroke="currentColor"></rect><path d="M8 8h8M8 12h6M8 16h8" stroke="currentColor" stroke-linecap="round"></path></svg><span>Context</span></button>
    </nav>
  </div>

  <div class="toast" id="toast" role="status" aria-live="polite"></div>

  <section class="sheet" id="unlockSheet" aria-hidden="true">
    <form class="sheet-panel" id="unlockForm">
      <h2>Unlock capture</h2>
      <p>Use the dashboard password or the app token. This only stores a device session cookie.</p>
      <div class="stack">
        <input name="username" autocomplete="username" placeholder="Username" value="chad" aria-label="Username">
        <input name="password" autocomplete="current-password" type="password" placeholder="Password or app token" aria-label="Password or app token">
        <button class="primary" type="submit">Unlock</button>
        <button class="secondary" type="button" id="closeUnlock">Not now</button>
      </div>
    </form>
  </section>

<script>
const validTabs = new Set(['today', 'body', 'capture', 'context']);
const requestedTab = new URLSearchParams(window.location.search).get('tab');
const state = { tab: validTabs.has(requestedTab) ? requestedTab : 'today', today: null, context: '', links: null, selectedIntent: 'strength_set' };
const screen = document.getElementById('screen');
const phaseLine = document.getElementById('phaseLine');
const toast = document.getElementById('toast');
const unlockSheet = document.getElementById('unlockSheet');

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function short(value, fallback = 'n/a') {
  if (value === null || value === undefined || value === '') return fallback;
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(n);
}
function signed(value, unit = '') {
  if (value === null || value === undefined || value === '') return 'n/a';
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  const formatted = new Intl.NumberFormat(undefined, { signDisplay: 'exceptZero', maximumFractionDigits: 2 }).format(n);
  return unit ? `${formatted} ${unit}` : formatted;
}
function compactRate(value, unit = '') {
  const compactUnit = unit === 'kg/week' ? 'kg/wk' : unit;
  return signed(value, compactUnit);
}
function valueWithUnit(value, unit = '') {
  if (value === null || value === undefined || value === '') return 'n/a';
  const suffix = unit || '';
  if (typeof value === 'string') {
    if (!suffix || value.toLowerCase().includes('source')) return value;
    return suffix === '%' ? `${value}%` : `${value} ${suffix}`;
  }
  const n = Number(value);
  if (!Number.isFinite(n)) return String(value);
  const digits = suffix === 'g/cm2' ? 3 : (suffix === 'g' ? 0 : 1);
  const rendered = new Intl.NumberFormat(undefined, { maximumFractionDigits: digits }).format(n);
  return suffix === '%' ? `${rendered}%` : (suffix ? `${rendered} ${suffix}` : rendered);
}
function metricByKey(metrics, key) {
  return (metrics || []).find(metric => metric.key === key) || {};
}
function shortDate(value) {
  if (!value) return 'n/a';
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric' }).format(date);
}
function toneClass(tone) {
  if (tone === 'green') return 'tone-green';
  if (tone === 'amber') return 'tone-amber';
  if (tone === 'coral' || tone === 'red') return 'tone-coral';
  return '';
}
function showToast(message) {
  toast.textContent = message;
  toast.classList.add('show');
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove('show'), 2500);
}
function openUnlock() {
  unlockSheet.classList.add('show');
  unlockSheet.setAttribute('aria-hidden', 'false');
  const password = unlockSheet.querySelector('input[type="password"]');
  if (password) window.setTimeout(() => password.focus(), 80);
}
function closeUnlock() {
  unlockSheet.classList.remove('show');
  unlockSheet.setAttribute('aria-hidden', 'true');
}
async function getJSON(path, options = {}) {
  const response = await fetch(path, { credentials: 'same-origin', ...options });
  if (response.status === 401) {
    openUnlock();
    throw new Error('Unlock required');
  }
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return await response.json();
}
async function load() {
  renderLoading();
  try {
    const [today, context] = await Promise.all([getJSON('/api/mobile/today'), getJSON('/api/mobile/context')]);
    state.today = today;
    state.context = context.markdown || '';
    state.selectedIntent = today.capture?.quick_actions?.[0]?.intent || state.selectedIntent;
    phaseLine.textContent = today.phase?.title || 'Current phase';
    render();
  } catch (error) {
    if (!state.today && error.message !== 'Unlock required') {
      screen.innerHTML = `<section class="surface section empty">${esc(error.message)}</section>`;
    }
  }
}
function renderLoading() {
  if (state.today) return;
  screen.innerHTML = `
    <section class="surface summary stack" aria-label="Loading health summary"><div class="loading-line"></div><div class="loading-line" style="width: 72%"></div><div class="stat-strip"><div class="stat"><span>Loading</span><b>--</b></div><div class="stat"><span>Target</span><b>--</b></div><div class="stat"><span>Rate</span><b>--</b></div></div></section>
    <section class="surface section stack"><div class="loading-line"></div><div class="loading-line" style="width: 86%"></div><div class="loading-line" style="width: 64%"></div></section>`;
}
function setTab(tab) {
  state.tab = tab;
  document.querySelectorAll('.tab').forEach(button => {
    const active = button.dataset.tab === tab;
    button.classList.toggle('active', active);
    button.setAttribute('aria-current', active ? 'page' : 'false');
  });
  render();
  screen.scrollTop = 0;
}
function render() {
  if (state.tab === 'body') return renderBody();
  if (state.tab === 'capture') return renderCapture();
  if (state.tab === 'context') return renderContext();
  return renderToday();
}
function renderToday() {
  const today = state.today;
  if (!today) return renderLoading();
  const progress = today.progress || {};
  const reminders = today.not_done_today || [];
  const shown = reminders.slice(0, 3);
  const hiddenCount = Math.max(0, reminders.length - shown.length);
  const reminderMarkup = shown.length
    ? shown.map(item => `<li class="task-row"><span class="check" aria-hidden="true"></span><div><div class="task-title">${esc(item.title)}</div><div class="detail clamp">${esc(item.detail)}</div></div><span class="status-pill">${esc(item.due)}</span></li>`).join('')
    : '<li class="empty">No open adherence items surfaced.</li>';
  const tripwire = today.tripwire ? renderTripwire(today.tripwire) : '';
  const next = today.next_action || {};
  screen.innerHTML = `
    <section class="surface summary" aria-label="Today health state">
      <div class="row"><span class="kicker">Now</span><span class="status-pill">${esc(today.phase?.status || 'unknown')}</span></div>
      <div class="verdict"><span class="signal ${toneClass(today.overall?.tone)}" aria-hidden="true"></span><div><h2 class="phrase">${esc(today.overall?.phrase || today.overall?.state || 'Needs data')}</h2><div class="meta">Day ${esc(today.phase?.day_count ?? 0)} · ${esc(today.phase?.next_anchor || 'next anchor not set')}</div></div></div>
      <div class="stat-strip" aria-label="Progress stats">
        <div class="stat"><span>${esc(progress.primary_label || 'Trend')}</span><b>${esc(short(progress.primary_value))} ${esc(progress.primary_unit || '')}</b></div>
        <div class="stat"><span>Target</span><b>${esc(progress.target_label || 'unset')}</b></div>
        <div class="stat"><span>Rate</span><b>${esc(compactRate(progress.rate_value, progress.rate_unit || ''))}</b></div>
      </div>
    </section>
    <section class="surface section">
      <div class="section-title"><h2>Today</h2><button class="small-button" id="quickCapture" type="button">Log</button></div>
      <ul class="task-list">${reminderMarkup}</ul>
      ${hiddenCount ? `<div class="detail">${hiddenCount} more item${hiddenCount === 1 ? '' : 's'} in context.</div>` : ''}
    </section>
    ${tripwire}
    <section class="surface next"><div class="kicker">Next move</div><h3>${esc(next.title || 'No action surfaced')}</h3><div class="detail clamp">${esc(next.why || 'The model has not surfaced a specific move yet.')}</div></section>`;
  document.getElementById('quickCapture')?.addEventListener('click', () => setTab('capture'));
}
function renderTripwire(tripwire) {
  const severe = tripwire.severity === 'high' || tripwire.state === 'Triggered';
  return `<section class="surface banner ${severe ? 'high' : ''}"><span class="banner-rule" aria-hidden="true"></span><div><div class="row"><span class="kicker">Tripwire</span><span class="status-pill">${esc(tripwire.state || 'Watch')}</span></div><h3>${esc(tripwire.title || 'Review signal')}</h3><div class="detail clamp">${esc(tripwire.recommended_action || tripwire.evidence || '')}</div></div></section>`;
}
function renderBody() {
  const body = state.today?.body || {};
  const summary = body.summary || {};
  const metrics = body.metrics || [];
  const delta = summary.delta || {};
  const history = body.history || [];
  const dexaBf = metricByKey(metrics, 'dexa_bf');
  const estimatedBf = metricByKey(metrics, 'estimated_bf');
  const weight = metricByKey(metrics, 'weight_trend');
  const lean = metricByKey(metrics, 'dexa_lean');
  const appendicular = metricByKey(metrics, 'appendicular_lean');
  const vat = metricByKey(metrics, 'vat');
  const ratio = metricByKey(metrics, 'android_gynoid');
  const bmd = metricByKey(metrics, 'bone_density');
  const anchors = history.slice().reverse().map(row => `
    <li class="anchor-row">
      <div><div class="item-title">${esc(shortDate(row.scan_date))}</div><div class="anchor-metrics">BF ${esc(valueWithUnit(row.body_fat_pct, '%'))} · Lean ${esc(valueWithUnit(row.lean_bmc_kg, 'kg'))} · VAT ${esc(valueWithUnit(row.vat_mass_g, 'g'))}</div></div>
      <span class="status-pill">${esc(valueWithUnit(row.weight_kg, 'kg'))}</span>
    </li>`).join('');
  screen.innerHTML = `
    <section class="surface body-hero" aria-label="Body composition">
      <div class="row"><span class="kicker">Body composition</span><span class="status-pill">DEXA ${esc(summary.latest_dexa_date || 'n/a')}</span></div>
      <div class="scan-value"><strong>${esc(valueWithUnit(summary.body_fat_pct, '%'))}</strong><span>BodyStats DEXA body fat</span></div>
      <div class="body-grid">
        ${renderBodyTile('Weight', valueWithUnit(summary.weight_kg, 'kg'), 'DEXA scan')}
        ${renderBodyTile('Lean + BMC', valueWithUnit(summary.lean_bmc_kg, 'kg'), 'DEXA measured')}
        ${renderBodyTile('Fat mass', valueWithUnit(summary.fat_mass_kg, 'kg'), 'DEXA measured')}
        ${renderBodyTile('VAT', valueWithUnit(summary.vat_mass_g, 'g'), 'DEXA measured')}
      </div>
      ${renderBodyChart(body.chart_history || [])}
      <div class="detail">${esc(body.source_note || '')}</div>
    </section>
    <section class="surface section">
      <div class="section-title"><h2>Current Estimate</h2><span class="status-pill">${esc(estimatedBf.source_label || 'Estimated')}</span></div>
      <div class="body-grid">
        ${renderBodyTile('DEXA BF', valueWithUnit(dexaBf.value, dexaBf.unit), dexaBf.source_label)}
        ${renderBodyTile('Estimate', valueWithUnit(estimatedBf.value, estimatedBf.unit), estimatedBf.source_label)}
        ${renderBodyTile('Trend weight', valueWithUnit(weight.value, weight.unit), weight.source_label)}
        ${renderBodyTile('Appendicular', valueWithUnit(appendicular.value, appendicular.unit), appendicular.source_label)}
      </div>
    </section>
    <section class="surface section">
      <div class="section-title"><h2>DEXA Anchors</h2><span class="status-pill">${esc(summary.dexa_count || 0)} scans</span></div>
      <ul class="plain-list">${anchors || '<li class="empty">No DEXA scans connected.</li>'}</ul>
    </section>
    <section class="surface section">
      <div class="section-title"><h2>Delta</h2><span class="status-pill">${esc(delta.from_date || 'previous')} to ${esc(delta.to_date || 'latest')}</span></div>
      <div class="delta-grid">
        ${renderBodyTile('BF', signed(delta.body_fat_pct, 'pp'), 'since previous')}
        ${renderBodyTile('Lean', signed(delta.lean_bmc_kg, 'kg'), 'since previous')}
        ${renderBodyTile('VAT', signed(delta.vat_mass_g, 'g'), 'since previous')}
      </div>
      <div class="body-grid">
        ${renderBodyTile('A/G ratio', valueWithUnit(ratio.value, ratio.unit), ratio.source_label)}
        ${renderBodyTile('BMD', valueWithUnit(bmd.value, bmd.unit), bmd.source_label)}
      </div>
    </section>`;
}
function renderBodyTile(label, value, source) {
  return `<div class="body-tile"><b>${esc(value || 'n/a')}</b><span>${esc(label)}${source ? ` · ${esc(source)}` : ''}</span></div>`;
}
function renderBodyChart(history) {
  const points = (history || [])
    .map(row => ({ date: row.scan_date, value: Number(row.body_fat_pct) }))
    .filter(point => point.date && Number.isFinite(point.value));
  if (points.length < 2) return '<div class="empty">Add another DEXA scan for trend.</div>';
  const values = points.map(point => point.value);
  const minY = Math.min(...values) - Math.max((Math.max(...values) - Math.min(...values)) * 0.28, 0.8);
  const maxY = Math.max(...values) + Math.max((Math.max(...values) - Math.min(...values)) * 0.28, 0.8);
  const coords = points.map((point, index) => {
    const x = 8 + (index / Math.max(points.length - 1, 1)) * 84;
    const y = 84 - ((point.value - minY) / Math.max(maxY - minY, 0.1)) * 64;
    return { ...point, x, y };
  });
  const line = coords.map(point => `${point.x.toFixed(2)},${point.y.toFixed(2)}`).join(' ');
  const dots = coords.map(point => `<circle class="chart-dot" cx="${point.x.toFixed(2)}" cy="${point.y.toFixed(2)}" r="3"><title>${esc(point.date)}: ${esc(valueWithUnit(point.value, '%'))}</title></circle>`).join('');
  return `<svg class="body-chart" viewBox="0 0 100 100" role="img" aria-label="DEXA body fat trend">
    <path class="chart-grid" d="M8 20H92M8 40H92M8 60H92M8 80H92"></path>
    <path class="chart-axis" d="M8 84H92"></path>
    <polyline class="chart-line" points="${line}"></polyline>
    ${dots}
    <text class="chart-label" x="8" y="95">${esc(shortDate(points[0].date))}</text>
    <text class="chart-label" x="92" y="95" text-anchor="end">${esc(shortDate(points[points.length - 1].date))}</text>
  </svg>`;
}
function renderCapture() {
  const today = state.today;
  const capture = today?.capture || {};
  const actions = capture.quick_actions || [{ intent: 'event', label: 'Event' }];
  const examples = capture.examples || [];
  const recent = today?.recent_capture || [];
  const selected = actions.find(action => action.intent === state.selectedIntent) || actions[0] || {};
  screen.innerHTML = `
    <section class="surface capture-card">
      <div class="row"><div><div class="kicker">Capture</div><h2>Quick log</h2></div><span class="status-pill">${esc(selected.label || 'Event')}</span></div>
      <div class="segmented capture-intents" role="tablist" aria-label="Capture type">${actions.map(action => `<button class="segmented-button ${state.selectedIntent === action.intent ? 'active' : ''}" type="button" data-intent="${esc(action.intent)}">${esc(action.label)}</button>`).join('')}</div>
      <textarea id="captureText" placeholder="${esc(capture.primary_prompt || 'What happened today?')}" aria-label="Health note"></textarea>
      <button class="primary" id="submitCapture" type="button" aria-label="Log health note">Log</button>
      <details class="quick-drawer"><summary>Quick fill</summary><div class="quick-note">${examples.map(example => `<button class="segmented-button" type="button" data-example="${esc(example)}">${esc(example)}</button>`).join('')}</div></details>
    </section>
    <section class="surface section"><div class="section-title"><h2>Recent</h2><span class="status-pill">${esc(capture.write_status || 'unknown')}</span></div><ul class="plain-list">${recent.length ? recent.map(item => `<li class="recent-row"><div class="item-title">${esc(item.title)}</div><div class="detail clamp">${esc(item.detail)}</div><div class="detail">${esc(item.occurred_at)}</div></li>`).join('') : '<li class="empty">No app captures yet.</li>'}</ul></section>`;
  screen.querySelectorAll('[data-intent]').forEach(button => button.addEventListener('click', () => {
    state.selectedIntent = button.dataset.intent;
    renderCapture();
  }));
  screen.querySelectorAll('[data-example]').forEach(button => button.addEventListener('click', () => {
    const input = document.getElementById('captureText');
    input.value = button.dataset.example || '';
    input.focus();
  }));
  document.getElementById('submitCapture')?.addEventListener('click', submitCapture);
}
async function submitCapture() {
  const input = document.getElementById('captureText');
  const text = input?.value.trim() || '';
  if (!text) {
    showToast('Add a note first');
    input?.focus();
    return;
  }
  try {
    const result = await getJSON('/api/mobile/capture', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ intent: state.selectedIntent, text, source: 'pwa', fields: {} }),
    });
    showToast(result.summary || 'Logged');
    await load();
    setTab('today');
  } catch (error) {
    if (error.message !== 'Unlock required') showToast(error.message);
  }
}
function renderContext() {
  const links = state.links;
  screen.innerHTML = `
    <section class="surface section"><div class="row"><div><div class="kicker">Context</div><h2>Protocol packet</h2></div><button class="small-button" id="copyContext" type="button">Copy</button></div></section>
    <section class="surface context-box">${esc(state.context || 'Context unavailable.')}</section>
    <section class="surface section"><div class="section-title"><h2>Projects</h2><button class="small-button" id="loadLinks" type="button">Refresh</button></div><div id="linksBox" class="stack">${renderLinks(links)}</div></section>`;
  document.getElementById('copyContext')?.addEventListener('click', copyContext);
  document.getElementById('loadLinks')?.addEventListener('click', loadLinks);
}
function renderLinks(links) {
  if (!links) return '<div class="detail">Links are private until unlocked.</div>';
  const items = [];
  if (links.claude_project_url) items.push(`<a class="secondary" href="${esc(links.claude_project_url)}">Claude project</a>`);
  if (links.chatgpt_project_url) items.push(`<a class="secondary" href="${esc(links.chatgpt_project_url)}">ChatGPT project</a>`);
  return items.length ? items.join('') : '<div class="empty">No project links configured.</div>';
}
async function copyContext() {
  try {
    await navigator.clipboard.writeText(state.context || '');
    showToast('Copied');
  } catch (_error) {
    showToast('Copy unavailable');
  }
}
async function loadLinks() {
  try {
    state.links = await getJSON('/api/mobile/links');
    renderContext();
  } catch (error) {
    if (error.message !== 'Unlock required') showToast(error.message);
  }
}
function renderMore() {
  const today = state.today || {};
  const capture = today.capture || {};
  screen.innerHTML = `
    <section class="surface section"><div class="section-title"><h2>Status</h2><span class="status-pill">PWA</span></div><ul class="plain-list">
      <li class="status-row"><div class="item-title">Capture writes</div><div class="detail">${esc(capture.write_status || 'unknown')}</div></li>
      <li class="status-row"><div class="item-title">Generated</div><div class="detail">${esc(today.generated_at || 'unknown')}</div></li>
      <li class="status-row"><div class="item-title">Dashboard</div><div class="detail"><a href="/dashboard">Open full view</a></div></li>
      <li class="status-row"><div class="item-title">API</div><div class="detail"><a href="/api/mobile/today">Today JSON</a></div></li>
    </ul></section>`;
}

document.querySelectorAll('.tab').forEach(button => button.addEventListener('click', () => setTab(button.dataset.tab)));
document.getElementById('refreshButton').addEventListener('click', load);
document.getElementById('closeUnlock').addEventListener('click', closeUnlock);
unlockSheet.addEventListener('click', event => { if (event.target === unlockSheet) closeUnlock(); });
document.getElementById('unlockForm').addEventListener('submit', async event => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const password = String(form.get('password') || '');
  const username = String(form.get('username') || 'chad');
  try {
    await getJSON('/api/mobile/session', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ username, password, token: password }),
    });
    closeUnlock();
    showToast('Unlocked');
    await load();
  } catch (_error) {
    showToast('Unlock failed');
  }
});
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/app/service-worker.js?v=3').catch(() => {});
setTab(state.tab);
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
            "background_color": "#f5f2ea",
            "theme_color": "#f5f2ea",
            "icons": [
                {"src": "/app/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any maskable"}
            ],
        },
        separators=(",", ":"),
    )


def render_service_worker() -> str:
    return """const CACHE = 'health-companion-v3';
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
  <rect width="512" height="512" rx="96" fill="#f5f2ea"/>
  <rect x="86" y="86" width="340" height="340" rx="72" fill="#fffdf7" stroke="#141814" stroke-width="18"/>
  <path d="M160 263l67 64 129-151" fill="none" stroke="#1f7a4d" stroke-width="34" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="356" cy="156" r="24" fill="#bf4338"/>
</svg>"""
