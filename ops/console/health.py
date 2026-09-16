"""Health tracker widget for the ops console.

This module is intentionally dumb: it reads a JSON snapshot produced by
`health-tracker` and never imports DuckDB or health internals. That keeps the
life dashboard zero-token and cheap to render.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

NAME = "health"
TITLE = "Health"
ORDER = 35

SNAPSHOT = Path.home() / ".local" / "state" / "health-tracker-widget.json"
STALE_HOURS = 3


def _load() -> dict:
    try:
        return json.loads(SNAPSHOT.read_text())
    except FileNotFoundError:
        return {}


def _age_hours(value: str | None) -> float | None:
    if not value:
        return None
    try:
        generated = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - generated).total_seconds() / 3600


def collect() -> list[dict]:
    data = _load()
    if not data:
        return [{
            "status": "bad",
            "needs_you": True,
            "title": "health widget snapshot missing",
            "detail": f"expected {SNAPSHOT}",
        }]

    age = _age_hours(data.get("generated_at"))
    items = []
    if age is None or age > STALE_HOURS:
        items.append({
            "status": "warn",
            "title": "health widget snapshot stale",
            "detail": f"last generated {data.get('generated_at') or 'unknown'}",
        })

    for item in data.get("items", []):
        items.append({
            "status": item.get("status", "info"),
            "title": item.get("title", "health status"),
            "detail": item.get("detail", ""),
            "needs_you": bool(item.get("needs_you", False)),
        })

    return items or [{"status": data.get("status", "info"), "title": "health snapshot loaded"}]


def summary() -> dict:
    data = _load()
    if not data:
        return {"value": "—", "label": "health", "sub": "snapshot missing", "status": "bad"}
    summary_data = data.get("summary", {})
    weight = summary_data.get("weight_kg")
    body_fat = summary_data.get("body_fat_pct")
    stale_count = summary_data.get("hae_stale_count")
    stream_count = summary_data.get("hae_stream_count")
    value = f"{weight:.1f} kg" if isinstance(weight, (int, float)) else "—"
    parts = []
    if isinstance(body_fat, (int, float)):
        parts.append(f"{body_fat:.1f}% BF")
    if stream_count is not None:
        parts.append(f"{stream_count} HAE streams")
    if stale_count:
        parts.append(f"{stale_count} stale")
    return {
        "value": value,
        "label": "latest weight",
        "sub": " · ".join(parts) if parts else "health tracker",
        "status": data.get("status", "info"),
    }
