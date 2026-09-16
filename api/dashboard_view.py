from __future__ import annotations

from datetime import date, datetime
from html import escape
from typing import Any


def render_dashboard(model: dict[str, Any]) -> str:
    tone = escape(model.get("overall", {}).get("tone", "amber"))
    status = escape(model.get("overall", {}).get("phrase", "Insufficient data"))
    goal = model.get("goal", {})
    hero = model.get("hero", {})
    body = model.get("body", {})
    performance = model.get("performance", {})
    tripwires = model.get("tripwires", [])
    intervention = model.get("intervention", {})
    modules = model.get("modules", {})

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Health Optimization Dashboard</title>
  <style>{_css()}</style>
</head>
<body class="tone-{tone}">
  <header class="topbar">
    <div>
      <p class="kicker">Health Optimization Dashboard</p>
      <h1>{status}</h1>
    </div>
    <div class="status-block">
      <span class="status-pill">{status}</span>
      <span class="freshness">{_freshness_label(model.get('freshness', {}))}</span>
    </div>
  </header>

  <nav class="tabs" aria-label="Primary navigation">
    {_tabs()}
  </nav>

  <main class="layout">
    <section class="main-stack">
      {_global_header(goal, hero)}
      {_hero_panel(hero)}
      <section class="split">
        {_body_panel(body)}
        {_performance_panel(performance)}
      </section>
      {_timeline_panel(model.get('timeline', {}))}
      {_future_modules(modules)}
    </section>
    {_tripwire_rail(tripwires, intervention)}
  </main>
</body>
</html>
"""


def _global_header(goal: dict[str, Any], hero: dict[str, Any]) -> str:
    ranges = "".join(f"<button {'class=active' if item == '30D' else ''}>{item}</button>" for item in ["7D", "30D", "90D", "1Y", "All"])
    return f"""
      <section class="global-grid">
        <div>
          <p class="label">Current primary goal</p>
          <h2>{_txt(goal.get('title'))}</h2>
          <p class="subtle">{_txt(goal.get('status'))} · started {_txt(goal.get('start_date'))} · next anchor {_txt(goal.get('next_anchor'))}</p>
        </div>
        <div class="range" aria-label="Time range selector">{ranges}</div>
        <div class="goal-box">
          <span class="label">Target band</span>
          <strong>{_range(goal.get('target_weight_band_kg'), 'kg')}</strong>
          <span>{_txt(goal.get('open_decision'))}</span>
        </div>
      </section>
    """


def _hero_panel(hero: dict[str, Any]) -> str:
    latest_dexa = hero.get("latest_dexa") or {}
    estimate = hero.get("estimate") or {}
    delta = hero.get("previous_dexa_delta") or {}
    weight = hero.get("smoothed_weight_kg")
    band = hero.get("target_weight_band_kg") or []
    progress = _band_progress(weight, band)
    return f"""
      <section class="panel hero-panel">
        <div class="hero-copy">
          <div class="panel-head">
            <div>
              <p class="label">Body trajectory</p>
              <h2>{_fmt(weight, 'kg')}</h2>
            </div>
            <span class="date-chip">as of {_txt(hero.get('as_of'))}</span>
          </div>
          <div class="progress-track" aria-label="Progress toward target weight band">
            <span class="target-band" style="left:{progress['band_left']}%;width:{progress['band_width']}%"></span>
            <span class="progress-dot" style="left:{progress['dot']}%"></span>
          </div>
          <div class="stat-grid four">
            {_stat('Current rate', _fmt_signed(hero.get('current_rate_kg_per_week'), 'kg/wk'), hero.get('provenance', {}).get('smoothed_weight_kg'))}
            {_stat('Projected target', _txt(hero.get('projected_target_date') or 'off pace'), None)}
            {_stat('DEXA body fat', _fmt(latest_dexa.get('body_fat_pct'), '%'), hero.get('provenance', {}).get('dexa_anchor'))}
            {_stat('Est. body fat', _fmt(estimate.get('range_label'), '%'), estimate.get('provenance'))}
          </div>
        </div>
        <div class="hero-chart">
          {_bodyfat_chart(hero)}
        </div>
        <div class="delta-strip">
          <span>Last DEXA {_txt(latest_dexa.get('scan_date'))}</span>
          <strong>{_fmt(latest_dexa.get('fat_mass_kg'), 'kg fat')}</strong>
          <strong>{_fmt(latest_dexa.get('lean_bmc_kg'), 'kg lean+BMC')}</strong>
          <strong>{_fmt(latest_dexa.get('vat_mass_g'), 'g VAT')}</strong>
          <span>Delta since previous: BF {_fmt_signed(delta.get('body_fat_pct'), 'pp')}, lean {_fmt_signed(delta.get('lean_bmc_kg'), 'kg')}</span>
        </div>
      </section>
    """


def _body_panel(body: dict[str, Any]) -> str:
    cards = "".join(_metric_tile(metric) for metric in body.get("metrics", []))
    return f"""
      <section class="panel">
        <div class="panel-head">
          <div>
            <p class="label">Body composition</p>
            <h2>DEXA anchors, Eufy trend</h2>
          </div>
          <span class="date-chip">latest DEXA {_txt(body.get('latest_dexa_date'))}</span>
        </div>
        <div class="metric-grid">{cards}</div>
      </section>
    """


def _performance_panel(performance: dict[str, Any]) -> str:
    cards = "".join(_metric_tile(metric) for metric in performance.get("metrics", []))
    return f"""
      <section class="panel">
        <div class="panel-head">
          <div>
            <p class="label">Performance</p>
            <h2>Activity and recovery</h2>
          </div>
          <span class="date-chip">anchor {_txt(performance.get('anchor_date'))}</span>
        </div>
        <div class="metric-grid">{cards}</div>
      </section>
    """


def _tripwire_rail(tripwires: list[dict[str, Any]], intervention: dict[str, Any]) -> str:
    items = "".join(_tripwire_card(item) for item in tripwires)
    return f"""
      <aside class="rail" aria-label="Tripwires">
        <section class="panel intervention">
          <p class="label">Today's intervention</p>
          <h2>{_txt(intervention.get('title'))}</h2>
          <p>{_txt(intervention.get('why'))}</p>
          <p class="evidence">{_txt('; '.join(intervention.get('supporting_measurements') or []))}</p>
          <div class="confidence">Confidence: <strong>{_txt(intervention.get('confidence'))}</strong></div>
          <div class="actions" aria-label="Intervention actions">
            <button>Accept</button><button>Modify</button><button>Dismiss</button>
          </div>
        </section>
        <section class="panel tripwires">
          <div class="panel-head">
            <div>
              <p class="label">Tripwire rail</p>
              <h2>{len(tripwires)} rules</h2>
            </div>
          </div>
          {items}
        </section>
      </aside>
    """


def _timeline_panel(timeline: dict[str, Any]) -> str:
    all_events = timeline.get("events", [])
    dexa_events = [e for e in all_events if e.get("type") == "DEXA"]
    workout_events = [e for e in all_events if e.get("type") != "DEXA"][-14:]
    events = sorted(dexa_events + workout_events, key=lambda e: str(e.get("date") or ""))[-18:]
    event_html = "".join(f"<span class='event {escape(str(e.get('type', '')).lower())}'>{_txt(e.get('date'))} · {_txt(e.get('type'))}</span>" for e in events)
    return f"""
      <section class="panel timeline-panel">
        <div class="panel-head">
          <div>
            <p class="label">Cause-and-effect timeline</p>
            <h2>{_txt(timeline.get('start'))} to {_txt(timeline.get('end'))}</h2>
          </div>
          <span class="date-chip">correlation only</span>
        </div>
        {_weight_chart(timeline)}
        <div class="event-lane">{event_html or '<span class="empty">Add source</span>'}</div>
      </section>
    """


def _future_modules(modules: dict[str, Any]) -> str:
    names = [("nutrition", "Nutrition"), ("bloodwork", "Bloodwork"), ("genetics", "Genetics"), ("experiments", "Experiments")]
    cards = []
    for key, label in names:
        state = (modules.get(key) or {}).get("state", "Add source")
        cards.append(f"<section class='module'><p class='label'>{escape(label)}</p><strong>{_txt(state)}</strong></section>")
    return f"<section class='module-grid'>{''.join(cards)}</section>"


def _metric_tile(metric: dict[str, Any]) -> str:
    value = metric.get("value")
    unit = metric.get("unit") or ""
    display = _fmt(value, unit) if value is not None else "Add source"
    return f"""
      <article class="metric-tile">
        <p>{_txt(metric.get('label'))}</p>
        <strong>{display}</strong>
        {_provenance(metric.get('provenance') or {'label': metric.get('source_label')})}
      </article>
    """


def _stat(label: str, value: str, provenance: dict[str, Any] | None) -> str:
    return f"""
      <article class="stat">
        <p>{escape(label)}</p>
        <strong>{value}</strong>
        {_provenance(provenance) if provenance else ''}
      </article>
    """


def _tripwire_card(item: dict[str, Any]) -> str:
    state_class = escape(str(item.get("state", "Data needed")).lower().replace(" ", "-"))
    return f"""
      <article class="tripwire {state_class}">
        <div class="tripwire-top">
          <strong>{_txt(item.get('title'))}</strong>
          <span>{_txt(item.get('state'))}</span>
        </div>
        <p class="rule">{_txt(item.get('rule'))}</p>
        <p>{_txt(item.get('evidence'))}</p>
        <dl>
          <dt>Source</dt><dd>{_txt(item.get('sources'))}</dd>
          <dt>Recency</dt><dd>{_txt(item.get('data_recency'))}</dd>
          <dt>Action</dt><dd>{_txt(item.get('recommended_action'))}</dd>
          <dt>Resolution</dt><dd>{_txt(item.get('resolution_condition'))}</dd>
        </dl>
      </article>
    """


def _provenance(prov: dict[str, Any] | None) -> str:
    if not prov:
        return ""
    label = _txt(prov.get("label") or "Source")
    rows = [
        ("Date", prov.get("date")),
        ("Device/provider", prov.get("device_provider")),
        ("Raw value", prov.get("raw_value")),
        ("Transformation", prov.get("transformation")),
        ("Confidence", prov.get("confidence")),
    ]
    details = "".join(f"<dt>{escape(k)}</dt><dd>{_txt(v)}</dd>" for k, v in rows)
    return f"<details class='provenance'><summary>{label}</summary><dl>{details}</dl></details>"


def _bodyfat_chart(hero: dict[str, Any]) -> str:
    latest = hero.get("latest_dexa") or {}
    estimate = hero.get("estimate") or {}
    points = []
    if latest.get("body_fat_pct") is not None:
        points.append((0, float(latest["body_fat_pct"]), "DEXA"))
    if estimate.get("body_fat_pct_mid") is not None:
        points.append((100, float(estimate["body_fat_pct_mid"]), "Estimate"))
    if len(points) < 2:
        return "<div class='chart-empty'>Add source</div>"
    values = [p[1] for p in points]
    ymin = min(values) - 1.2
    ymax = max(values) + 1.2
    def y(value: float) -> float:
        return 84 - ((value - ymin) / max(ymax - ymin, 0.1) * 68)
    line = f"0,{y(points[0][1]):.2f} 100,{y(points[1][1]):.2f}"
    band = estimate.get("body_fat_pct_range") or []
    band_rect = ""
    if len(band) == 2:
        y1, y2 = y(float(band[1])), y(float(band[0]))
        band_rect = f"<rect x='0' y='{y1:.2f}' width='100' height='{max(1, y2-y1):.2f}' class='confidence-band'/>"
    return f"""
      <svg class="chart" viewBox="0 0 100 100" role="img" aria-label="DEXA body fat to current calibrated estimate">
        {band_rect}
        <line x1="0" y1="84" x2="100" y2="84" class="axis"/>
        <polyline points="{line}" class="line estimated"/>
        <circle cx="0" cy="{y(points[0][1]):.2f}" r="3.5" class="dot dexa"/>
        <circle cx="100" cy="{y(points[1][1]):.2f}" r="3.5" class="dot estimate"/>
        <text x="2" y="95">DEXA</text><text x="98" y="95" text-anchor="end">Current est.</text>
      </svg>
    """


def _weight_chart(timeline: dict[str, Any]) -> str:
    series = timeline.get("series", {}).get("weight", [])
    if len(series) < 2:
        return "<div class='chart-empty'>Add source</div>"
    return _line_chart(series, "weight kg")


def _line_chart(series: list[dict[str, Any]], label: str) -> str:
    parsed = []
    for row in series:
        value = row.get("value")
        dt = _parse_date(row.get("date"))
        if dt is not None and value is not None:
            parsed.append((dt.toordinal(), float(value)))
    if len(parsed) < 2:
        return "<div class='chart-empty'>Add source</div>"
    min_x, max_x = min(p[0] for p in parsed), max(p[0] for p in parsed)
    min_y, max_y = min(p[1] for p in parsed), max(p[1] for p in parsed)
    pad = max((max_y - min_y) * 0.18, 0.4)
    min_y -= pad
    max_y += pad
    def pt(item: tuple[int, float]) -> str:
        x = 4 + ((item[0] - min_x) / max(max_x - min_x, 1) * 92)
        y = 86 - ((item[1] - min_y) / max(max_y - min_y, 0.1) * 72)
        return f"{x:.2f},{y:.2f}"
    points = " ".join(pt(item) for item in parsed)
    return f"""
      <svg class="wide-chart" viewBox="0 0 100 100" role="img" aria-label="{escape(label)} trend">
        <line x1="4" y1="86" x2="96" y2="86" class="axis"/>
        <polyline points="{points}" class="line measured"/>
      </svg>
    """


def _tabs() -> str:
    items = ["Overview", "Body", "Performance", "Nutrition", "Bloodwork", "Genetics", "Experiments", "Data & Rules"]
    return "".join(f"<a {'class=active' if item == 'Overview' else ''}>{escape(item)}</a>" for item in items)


def _freshness_label(freshness: dict[str, Any]) -> str:
    if not freshness:
        return "Data needed"
    if freshness.get("ok"):
        return f"{freshness.get('stream_count')} streams · max lag {freshness.get('max_lag_hours')} h"
    return f"{freshness.get('stale_count')} stale stream(s)"


def _band_progress(weight: Any, band: list[Any]) -> dict[str, float]:
    if weight is None or len(band) != 2:
        return {"dot": 50, "band_left": 35, "band_width": 30}
    low, high = float(band[0]), float(band[1])
    min_v, max_v = low - 1.5, high + 1.5
    def pos(value: float) -> float:
        return max(0, min(100, ((value - min_v) / (max_v - min_v)) * 100))
    return {"dot": pos(float(weight)), "band_left": pos(low), "band_width": max(3, pos(high) - pos(low))}


def _range(values: list[Any] | None, unit: str) -> str:
    if not values or len(values) != 2:
        return "Add source"
    return f"{values[0]}-{values[1]} {escape(unit)}"


def _fmt(value: Any, unit: str) -> str:
    if value is None or value == "":
        return "Add source"
    if isinstance(value, str):
        return f"{escape(value)} {escape(unit)}".strip()
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _txt(value)
    text = f"{number:,.1f}" if abs(number) >= 100 else f"{number:,.2f}".rstrip("0").rstrip(".")
    return f"{text} {escape(unit)}".strip()


def _fmt_signed(value: Any, unit: str) -> str:
    if value is None:
        return "Add source"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _txt(value)
    return f"{number:+.2f} {escape(unit)}"


def _txt(value: Any) -> str:
    if value is None or value == "":
        return "Add source"
    return escape(str(value))


def _parse_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _css() -> str:
    return """
:root {
  color-scheme: dark;
  --bg: #0d1010;
  --panel: #171c1b;
  --panel-2: #1d2422;
  --line: #303936;
  --text: #f2f0ea;
  --muted: #a7b1aa;
  --soft: #6e7972;
  --green: #62d28f;
  --amber: #e4b64f;
  --coral: #ff746e;
  --blue: #7fb0ff;
  --ink: #0f1312;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  letter-spacing: 0;
}
button, a { font: inherit; }
.topbar {
  min-height: 96px;
  padding: 24px clamp(16px, 3vw, 36px) 14px;
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: flex-end;
  border-bottom: 1px solid var(--line);
  background: #101413;
}
.kicker, .label { margin: 0 0 6px; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }
h1, h2 { margin: 0; line-height: 1.05; font-weight: 650; letter-spacing: 0; }
h1 { font-size: clamp(34px, 5vw, 72px); }
h2 { font-size: clamp(18px, 2vw, 25px); }
.subtle, .freshness { color: var(--muted); }
.status-block { display: flex; gap: 10px; align-items: center; justify-content: flex-end; flex-wrap: wrap; }
.status-pill, .date-chip {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 7px 10px;
  color: var(--text);
  background: #121716;
  font-size: 13px;
}
.tone-green .status-pill { border-color: rgba(98,210,143,.7); color: var(--green); }
.tone-amber .status-pill { border-color: rgba(228,182,79,.75); color: var(--amber); }
.tone-coral .status-pill { border-color: rgba(255,116,110,.75); color: var(--coral); }
.tabs {
  display: flex;
  gap: 4px;
  padding: 10px clamp(12px, 3vw, 36px);
  border-bottom: 1px solid var(--line);
  overflow-x: auto;
  background: #111514;
}
.tabs a {
  color: var(--muted);
  text-decoration: none;
  padding: 9px 12px;
  border: 1px solid transparent;
  border-radius: 6px;
  white-space: nowrap;
}
.tabs a.active { color: var(--text); background: var(--panel-2); border-color: var(--line); }
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 14px;
  padding: 14px clamp(12px, 3vw, 36px) 28px;
}
.main-stack { display: grid; gap: 14px; min-width: 0; }
.panel, .global-grid, .module {
  border: 1px solid var(--line);
  background: var(--panel);
  border-radius: 8px;
}
.global-grid {
  display: grid;
  grid-template-columns: minmax(260px, 1fr) auto minmax(210px, 320px);
  gap: 14px;
  align-items: center;
  padding: 16px;
}
.goal-box { display: grid; gap: 4px; padding-left: 14px; border-left: 1px solid var(--line); color: var(--muted); }
.goal-box strong { color: var(--text); font-size: 22px; font-variant-numeric: tabular-nums; }
.range { display: flex; background: #101413; border: 1px solid var(--line); border-radius: 7px; padding: 3px; }
.range button { border: 0; color: var(--muted); background: transparent; padding: 8px 9px; border-radius: 5px; min-width: 42px; }
.range button.active { background: var(--blue); color: var(--ink); }
.panel { padding: 16px; }
.panel-head { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 16px; }
.hero-panel { display: grid; grid-template-columns: minmax(0, 1fr) minmax(280px, 34%); gap: 16px; align-items: stretch; }
.hero-copy { min-width: 0; }
.hero-copy h2 { font-size: clamp(48px, 8vw, 96px); font-variant-numeric: tabular-nums; }
.progress-track { position: relative; height: 14px; margin: 18px 0 14px; border-radius: 999px; background: #0f1312; border: 1px solid var(--line); }
.target-band { position: absolute; top: 3px; bottom: 3px; border-radius: 999px; background: rgba(98,210,143,.35); }
.progress-dot { position: absolute; top: 50%; width: 18px; height: 18px; transform: translate(-50%, -50%); border-radius: 50%; background: var(--text); box-shadow: 0 0 0 4px rgba(127,176,255,.22); }
.stat-grid { display: grid; gap: 10px; }
.stat-grid.four { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.stat, .metric-tile, .module { padding: 12px; background: #141918; border: 1px solid #27302d; border-radius: 7px; min-width: 0; }
.stat p, .metric-tile p { margin: 0 0 6px; color: var(--muted); font-size: 13px; }
.stat strong, .metric-tile strong, .module strong { display: block; font-size: clamp(22px, 3vw, 34px); font-variant-numeric: tabular-nums; line-height: 1.05; overflow-wrap: anywhere; }
.hero-chart { background: #111514; border: 1px solid var(--line); border-radius: 7px; min-height: 240px; display: flex; align-items: center; justify-content: center; }
.chart, .wide-chart { width: 100%; height: 100%; min-height: 220px; }
.wide-chart { min-height: 170px; }
.axis { stroke: #3a4541; stroke-width: .7; }
.line { fill: none; stroke-width: 2.5; vector-effect: non-scaling-stroke; }
.line.measured { stroke: var(--blue); }
.line.estimated { stroke: var(--amber); stroke-dasharray: 4 3; }
.confidence-band { fill: rgba(228,182,79,.18); }
.dot.dexa { fill: var(--coral); }
.dot.estimate { fill: var(--amber); }
svg text { fill: var(--muted); font-size: 5px; letter-spacing: 0; }
.chart-empty, .empty { color: var(--muted); }
.delta-strip { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 12px; color: var(--muted); border-top: 1px solid var(--line); padding-top: 12px; }
.delta-strip strong { color: var(--text); font-variant-numeric: tabular-nums; }
.split { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.metric-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.provenance { margin-top: 8px; color: var(--muted); font-size: 12px; }
.provenance summary { cursor: pointer; color: var(--blue); }
dl { margin: 8px 0 0; display: grid; grid-template-columns: 92px minmax(0, 1fr); gap: 4px 12px; }
dt { color: var(--soft); }
dd { margin: 0; color: var(--muted); overflow-wrap: anywhere; line-height: 1.25; }
.rail { display: grid; align-content: start; gap: 14px; min-width: 0; }
.intervention h2 { color: var(--text); margin-bottom: 10px; }
.evidence { color: var(--muted); }
.confidence { margin: 10px 0; color: var(--muted); }
.actions { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.actions button { border: 1px solid var(--line); background: #101413; color: var(--text); border-radius: 6px; padding: 9px 6px; }
.actions button:first-child { background: var(--green); color: var(--ink); border-color: var(--green); }
.tripwires { display: grid; gap: 10px; }
.tripwire { padding: 12px; border: 1px solid var(--line); border-left-width: 4px; border-radius: 7px; background: #141918; }
.tripwire.triggered { border-left-color: var(--coral); }
.tripwire.watch, .tripwire.data-needed { border-left-color: var(--amber); }
.tripwire.resolved { border-left-color: var(--green); }
.tripwire-top { display: flex; justify-content: space-between; gap: 10px; align-items: center; }
.tripwire-top span { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }
.tripwire p { color: var(--muted); margin: 8px 0 0; }
.tripwire .rule { color: var(--text); }
.tripwire dl { grid-template-columns: 86px minmax(0, 1fr); }
.timeline-panel { min-height: 300px; }
.event-lane { display: flex; flex-wrap: wrap; gap: 8px; border-top: 1px solid var(--line); padding-top: 12px; }
.event { border: 1px solid var(--line); color: var(--muted); border-radius: 999px; padding: 6px 9px; font-size: 12px; }
.event.dexa { color: var(--coral); border-color: rgba(255,116,110,.55); }
.event.workout { color: var(--blue); border-color: rgba(127,176,255,.4); }
.module-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; }
.module strong { color: var(--blue); font-size: 24px; }
@media (max-width: 1180px) {
  .layout { grid-template-columns: 1fr; }
  .rail { grid-template-columns: 1fr; }
}
@media (max-width: 820px) {
  .topbar { align-items: flex-start; flex-direction: column; }
  .global-grid, .hero-panel, .split, .module-grid { grid-template-columns: 1fr; }
  .stat-grid.four, .metric-grid { grid-template-columns: 1fr 1fr; }
  .goal-box { border-left: 0; padding-left: 0; border-top: 1px solid var(--line); padding-top: 12px; }
}
@media (max-width: 520px) {
  .stat-grid.four, .metric-grid, .actions { grid-template-columns: 1fr; }
  .range { width: 100%; overflow-x: auto; }
  .tabs { padding-left: 8px; padding-right: 8px; }
  .layout { padding-left: 8px; padding-right: 8px; }
}
"""
