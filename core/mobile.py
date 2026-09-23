from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import duckdb

from core.dashboard import build_dashboard_model
from core.schema import DEFAULT_DB, connect, load_schema

ATTENTION_STATES = {"Triggered", "Watch", "Data needed"}
SEVERITY_RANK = {"high": 3, "medium": 2, "low": 1}
VANCOUVER = ZoneInfo("America/Vancouver")


def build_today_model(db_path: str | Path = DEFAULT_DB) -> dict[str, Any]:
    """Build the narrow mobile contract for the iOS Today screen."""
    dashboard = build_dashboard_model(db_path)
    goal = dashboard.get("goal") or {}
    hero = dashboard.get("hero") or {}
    tripwires = dashboard.get("tripwires") or []
    attention_tripwires = [item for item in tripwires if item.get("state") in ATTENTION_STATES]
    today = _local_today()

    return {
        "generated_at": dashboard.get("generated_at"),
        "overall": dashboard.get("overall") or {},
        "phase": _phase(goal),
        "progress": _progress(hero, goal),
        "body": _body_composition(dashboard.get("body") or {}, hero),
        "not_done_today": _not_done_today(dashboard, attention_tripwires, _has_strength_or_rest_today(db_path, today)),
        "tripwire": _top_tripwire(attention_tripwires),
        "next_action": _next_action(dashboard.get("intervention") or {}),
        "capture": _capture_contract(),
        "recent_capture": _recent_capture(db_path),
        "review_links": {
            "dashboard": "/dashboard",
            "overview_json": "/api/dashboard/overview",
            "context_packet": "/api/mobile/context",
        },
    }


def build_context_packet(db_path: str | Path = DEFAULT_DB) -> str:
    today = build_today_model(db_path)
    progress = today.get("progress") or {}
    body = today.get("body") or {}
    body_summary = body.get("summary") or {}
    next_action = today.get("next_action") or {}
    tripwire = today.get("tripwire")
    not_done = today.get("not_done_today") or []
    recent_capture = today.get("recent_capture") or []

    lines = [
        "# Health Context Packet",
        "",
        f"Generated: {today.get('generated_at') or 'unknown'}",
        f"Overall: {(today.get('overall') or {}).get('state') or 'unknown'}",
        "",
        "## Current Phase",
        f"- Name: {(today.get('phase') or {}).get('title') or 'unknown'}",
        f"- Status: {(today.get('phase') or {}).get('status') or 'unknown'}",
        f"- Day: {(today.get('phase') or {}).get('day_count') or 0}",
        "",
        "## Progress",
        f"- Primary metric: {progress.get('primary_label') or 'unknown'}",
        f"- Current: {_format_value(progress.get('primary_value'), progress.get('primary_unit'))}",
        f"- Target: {progress.get('target_label') or 'not configured'}",
        f"- Rate: {_format_value(progress.get('rate_value'), progress.get('rate_unit'))}",
        "",
        "## Body Composition",
        f"- Latest DEXA: {body_summary.get('latest_dexa_date') or 'not available'}",
        f"- DEXA body fat: {_format_value(body_summary.get('body_fat_pct'), '%')}",
        f"- Estimated current body fat: {_format_value(body_summary.get('estimated_body_fat_range'), '%')}",
        f"- DEXA lean + BMC: {_format_value(body_summary.get('lean_bmc_kg'), 'kg')}",
        f"- DEXA fat mass: {_format_value(body_summary.get('fat_mass_kg'), 'kg')}",
        f"- VAT: {_format_value(body_summary.get('vat_mass_g'), 'g')}",
        "",
        "## Not Done Today",
    ]
    if not_done:
        lines.extend(f"- [{item.get('state', 'open')}] {item.get('title')} - {item.get('detail')}" for item in not_done)
    else:
        lines.append("- None currently surfaced by deterministic rules.")

    lines.extend(["", "## Recent Capture"])
    if recent_capture:
        lines.extend(f"- {item.get('occurred_at')}: {item.get('title')} - {item.get('detail')}" for item in recent_capture)
    else:
        lines.append("- None logged yet.")

    lines.extend(["", "## Active Tripwire"])
    if tripwire:
        lines.extend(
            [
                f"- {tripwire.get('title')} ({tripwire.get('state')}, {tripwire.get('severity')})",
                f"- Evidence: {tripwire.get('evidence')}",
                f"- Action: {tripwire.get('recommended_action')}",
                f"- Resolution: {tripwire.get('resolution_condition')}",
            ]
        )
    else:
        lines.append("- None active.")

    lines.extend(
        [
            "",
            "## Next Action",
            f"- {next_action.get('title') or 'No action surfaced.'}",
            f"- Why: {next_action.get('why') or 'n/a'}",
            f"- Review: {next_action.get('review_date') or 'not scheduled'}",
            "",
            "## Analyst Rules",
            "- Use deterministic tripwires as authority; do not invent thresholds.",
            "- DEXA/labs decide; watch and scale track.",
            "- If the subject overrides, log it once without arguing.",
            "- One recommendation should name the phase, metric, and review date.",
        ]
    )
    return "\n".join(lines) + "\n"


def _phase(goal: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": goal.get("title") or "Current phase unconfirmed",
        "status": goal.get("status") or "unknown",
        "day_count": goal.get("days_elapsed") or 0,
        "next_anchor": goal.get("next_anchor"),
        "open_decision": goal.get("open_decision"),
    }


def _progress(hero: dict[str, Any], goal: dict[str, Any]) -> dict[str, Any]:
    target_band = hero.get("target_weight_band_kg") or goal.get("target_weight_band_kg")
    latest_dexa = hero.get("latest_dexa") or {}
    estimate = hero.get("estimate") or {}
    return {
        "primary_label": "7-day weight trend",
        "primary_value": hero.get("smoothed_weight_kg"),
        "primary_unit": "kg",
        "target_band": target_band,
        "target_label": _target_band_label(target_band, "kg"),
        "rate_value": hero.get("current_rate_kg_per_week"),
        "rate_unit": "kg/week",
        "projected_target_date": hero.get("projected_target_date"),
        "goal_delta_kg": hero.get("goal_delta_kg"),
        "latest_dexa": latest_dexa,
        "estimate": {
            "available": estimate.get("available", False),
            "body_fat_range": estimate.get("range_label"),
            "confidence": estimate.get("confidence"),
        },
    }


def _body_composition(body: dict[str, Any], hero: dict[str, Any]) -> dict[str, Any]:
    metrics = body.get("metrics") or []
    history = body.get("dexa_history") or []
    latest_dexa = hero.get("latest_dexa") or (history[-1] if history else {})
    estimate = hero.get("estimate") or {}
    delta = body.get("dexa_delta") or hero.get("previous_dexa_delta") or {}
    visible_metric_keys = {
        "weight_trend",
        "dexa_bf",
        "estimated_bf",
        "dexa_lean",
        "appendicular_lean",
        "vat",
        "android_gynoid",
        "bone_density",
    }
    selected_metrics = [metric for metric in metrics if metric.get("key") in visible_metric_keys]
    chart_history = [
        {
            "scan_date": row.get("scan_date"),
            "body_fat_pct": row.get("body_fat_pct"),
            "weight_kg": row.get("weight_kg"),
            "lean_bmc_kg": row.get("lean_bmc_kg"),
            "vat_mass_g": row.get("vat_mass_g"),
        }
        for row in history[-8:]
    ]
    return {
        "summary": {
            "latest_dexa_date": body.get("latest_dexa_date") or latest_dexa.get("scan_date"),
            "dexa_count": body.get("dexa_count") or len(history),
            "provider": latest_dexa.get("provider"),
            "weight_kg": latest_dexa.get("weight_kg"),
            "body_fat_pct": latest_dexa.get("body_fat_pct"),
            "estimated_body_fat_range": estimate.get("range_label"),
            "fat_mass_kg": latest_dexa.get("fat_mass_kg"),
            "lean_bmc_kg": latest_dexa.get("lean_bmc_kg"),
            "appendicular_lean_bmc_kg": latest_dexa.get("appendicular_lean_bmc_kg"),
            "vat_mass_g": latest_dexa.get("vat_mass_g"),
            "android_gynoid_ratio": latest_dexa.get("android_gynoid_ratio"),
            "bmd_total_g_cm2": latest_dexa.get("bmd_total_g_cm2"),
            "delta": delta,
        },
        "metrics": selected_metrics,
        "history": history[-6:],
        "chart_history": chart_history,
        "source_note": "DEXA anchors stay separate from Eufy BIA; estimates are DEXA-calibrated trend values.",
    }


def _not_done_today(dashboard: dict[str, Any], tripwires: list[dict[str, Any]], strength_or_rest_today: bool) -> list[dict[str, str]]:
    goal = dashboard.get("goal") or {}
    freshness = dashboard.get("freshness") or {}
    performance = dashboard.get("performance") or {}
    modules = dashboard.get("modules") or {}
    items: list[dict[str, str]] = []

    if not freshness.get("ok"):
        items.append(
            _reminder(
                "restore-hae",
                "Restore Health Auto Export",
                f"{freshness.get('stale_count', 1)} stale stream(s); daily state is not trustworthy until sync is fresh.",
                "today",
            )
        )

    if goal.get("open_decision"):
        items.append(_reminder("confirm-phase", "Confirm current phase", str(goal["open_decision"]), "today"))

    strength_metric = _metric_by_label(performance.get("metrics") or [], "Strength progression")
    if not strength_or_rest_today and (not strength_metric or strength_metric.get("source_label") == "Add source"):
        items.append(
            _reminder(
                "strength-log",
                "Log strength or rest day",
                "Strength source is not connected; capture sets, RPE, or explicitly log rest.",
                "today",
            )
        )

    if (modules.get("experiments") or {}).get("state") == "Add source":
        items.append(
            _reminder(
                "experiment-ledger",
                "Log interventions and overrides",
                "Fasts, symptom clusters, skipped sessions, and protocol overrides need event records.",
                "when applicable",
            )
        )

    if any(t.get("id") == "data-freshness" and t.get("state") == "Triggered" for t in tripwires):
        items = [item for item in items if item["id"] != "restore-hae"] + [
            _reminder("restore-hae", "Restore Health Auto Export", "Tripwire fired: Health Auto Export is stale.", "now")
        ]

    return items[:4]


def _top_tripwire(tripwires: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not tripwires:
        return None
    return sorted(
        tripwires,
        key=lambda item: (SEVERITY_RANK.get(item.get("severity", "low"), 0), item.get("state") == "Triggered"),
        reverse=True,
    )[0]


def _next_action(intervention: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": intervention.get("title"),
        "why": intervention.get("why"),
        "supporting_measurements": intervention.get("supporting_measurements") or [],
        "confidence": intervention.get("confidence"),
        "review_date": intervention.get("review_date"),
        "source_tripwire": intervention.get("source_tripwire"),
    }


def _capture_contract() -> dict[str, Any]:
    return {
        "primary_prompt": "What happened today?",
        "endpoint": "/api/mobile/capture",
        "auth_required": True,
        "examples": [
            "KB press 24 kg 3x8 RPE 8",
            "Rest day; sleep debt and HRV strain",
            "Skipped swim; fatigue and heat after lifting",
            "36 h fast started 20:00, electrolytes ok",
            "Override: trained despite HRV strain",
            "weight 81.2 kg",
        ],
        "quick_actions": [
            {"intent": "strength_set", "label": "Strength"},
            {"intent": "event", "label": "Event"},
            {"intent": "manual_reading", "label": "Reading"},
            {"intent": "override", "label": "Override"},
            {"intent": "symptom", "label": "Symptom"},
            {"intent": "phase_decision", "label": "Phase"},
        ],
        "intents": ["strength_set", "event", "manual_reading", "override", "symptom", "phase_decision"],
        "write_status": "enabled",
    }


def _has_strength_or_rest_today(db_path: str | Path, today: date) -> bool:
    conn = _open_mobile_read_conn(db_path)
    try:
        strength_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM strength_sets
            WHERE session_date = ?
            """,
            [today],
        ).fetchone()[0]
        rest_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM events
            WHERE CAST(start_ts AS DATE) = ? AND kind IN ('rest_day', 'strength_session')
            """,
            [today],
        ).fetchone()[0]
        return int(strength_count or 0) + int(rest_count or 0) > 0
    finally:
        conn.close()


def _recent_capture(db_path: str | Path, limit: int = 5) -> list[dict[str, str]]:
    conn = _open_mobile_read_conn(db_path)
    try:
        rows: list[dict[str, Any]] = []
        rows.extend(
            {
                "occurred_at": row[0],
                "source": "event",
                "title": str(row[1] or "event"),
                "detail": str(row[2] or ""),
            }
            for row in conn.execute(
                """
                SELECT start_ts, kind, notes
                FROM events
                WHERE start_ts IS NOT NULL
                ORDER BY start_ts DESC
                LIMIT ?
                """,
                [limit],
            ).fetchall()
        )
        rows.extend(
            {
                "occurred_at": row[0],
                "source": "override",
                "title": "override",
                "detail": str(row[1] or row[2] or ""),
            }
            for row in conn.execute(
                """
                SELECT ts, decision, reason
                FROM overrides
                WHERE ts IS NOT NULL
                ORDER BY ts DESC
                LIMIT ?
                """,
                [limit],
            ).fetchall()
        )
        rows.extend(
            {
                "occurred_at": row[0],
                "source": "reading",
                "title": str(row[1] or "reading"),
                "detail": _format_value(row[2], row[3]),
            }
            for row in conn.execute(
                """
                SELECT ts, metric, value, unit
                FROM readings
                WHERE ts IS NOT NULL
                ORDER BY ts DESC
                LIMIT ?
                """,
                [limit],
            ).fetchall()
        )
        rows.extend(
            {
                "occurred_at": row[0],
                "source": "strength_set",
                "title": str(row[1] or "strength"),
                "detail": f"{row[2]} reps" + (f" at {row[3]:g} kg" if row[3] is not None else ""),
            }
            for row in conn.execute(
                """
                SELECT session_date, exercise, reps, load_kg
                FROM strength_sets
                ORDER BY session_date DESC, set_no DESC
                LIMIT ?
                """,
                [limit],
            ).fetchall()
        )
        rows = sorted(rows, key=lambda item: str(item["occurred_at"] or ""), reverse=True)[:limit]
        return [
            {
                "occurred_at": item["occurred_at"].isoformat() if hasattr(item["occurred_at"], "isoformat") else str(item["occurred_at"]),
                "source": str(item["source"]),
                "title": str(item["title"]),
                "detail": str(item["detail"]),
            }
            for item in rows
        ]
    finally:
        conn.close()


def _local_today() -> date:
    return datetime.now(VANCOUVER).date()


def _open_mobile_read_conn(db_path: str | Path) -> duckdb.DuckDBPyConnection:
    path = Path(db_path)
    if path.exists():
        try:
            return duckdb.connect(str(path), read_only=True)
        except duckdb.IOException:
            return connect(path)
    conn = connect(path)
    load_schema(conn)
    return conn


def _metric_by_label(metrics: list[dict[str, Any]], label: str) -> dict[str, Any] | None:
    for metric in metrics:
        if metric.get("label") == label:
            return metric
    return None


def _reminder(item_id: str, title: str, detail: str, due: str) -> dict[str, str]:
    return {"id": item_id, "title": title, "detail": detail, "due": due, "state": "open"}


def _target_band_label(target_band: Any, unit: str) -> str | None:
    if isinstance(target_band, list) and len(target_band) == 2:
        return f"{target_band[0]}-{target_band[1]} {unit}"
    return None


def _format_value(value: Any, unit: Any) -> str:
    if value is None:
        return "not available"
    return f"{value} {unit or ''}".strip()
