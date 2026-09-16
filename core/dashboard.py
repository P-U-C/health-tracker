from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from math import isfinite
from pathlib import Path
from statistics import median, pstdev
from typing import Any

import duckdb

from core.schema import DEFAULT_DB, connect, load_schema

MAX_HAE_LAG_HOURS = 36
WEIGHT_BAND_KG = (70.5, 71.5)
WEIGHT_GOAL_START = date(2026, 9, 4)
NEXT_DEXA_ANCHOR = "December 2026"


def build_dashboard_model(db_path: str | Path = DEFAULT_DB) -> dict[str, Any]:
    path = Path(db_path)
    conn = _open_dashboard_conn(path)
    try:
        freshness = _freshness(conn)
        dexa_rows = _rows(
            conn,
            """
            SELECT scan_date, provider, weight_kg, body_fat_pct, fat_mass_kg, lean_bmc_kg,
                   appendicular_lean_bmc_kg, vat_mass_g, vat_area_cm2, android_gynoid_ratio,
                   bmd_total_g_cm2, bmd_t_score, bmd_z_score, source_file
            FROM dexa_scans
            ORDER BY scan_date
            """,
        )
        eufy_weight = _body_series(conn, "weight_kg")
        eufy_bf = _body_series(conn, "body_fat_pct")
        eufy_lean = _body_series(conn, "lean_mass_kg")
        daily = _daily_metrics(conn)
        workouts = _workout_daily(conn)
        hrv = _hrv_daily(conn)
        rhr = _rows(conn, "SELECT date, resting_hr FROM resting_hr ORDER BY date")
        vo2 = _latest(conn, "SELECT date, vo2max FROM vo2max ORDER BY date DESC LIMIT 1")
        sleep = _sleep_daily(conn)
    finally:
        conn.close()

    anchor_date = _max_date(eufy_weight, eufy_bf, daily, workouts, rhr, dexa_rows) or date.today()
    latest_dexa = dexa_rows[-1] if dexa_rows else None
    previous_dexa = dexa_rows[-2] if len(dexa_rows) >= 2 else None

    weight_now = _window_median(eufy_weight, anchor_date, 7)
    weight_prior = _window_median(eufy_weight, anchor_date - timedelta(days=7), 7)
    weight_rate_week = _delta(weight_now, weight_prior)
    weight_start = _nearest_value(eufy_weight, WEIGHT_GOAL_START, max_days=3)
    weight_delta_goal = _delta(weight_now, weight_start)

    bf_now = _window_median(eufy_bf, anchor_date, 7)
    lean_now = _window_median(eufy_lean, anchor_date, 7)
    calibration = _calibration(dexa_rows, eufy_bf)
    estimate = _dexa_anchored_estimate(weight_now, bf_now, calibration)

    composition = _composition_summary(latest_dexa, previous_dexa, weight_now, bf_now, lean_now, estimate)
    performance = _performance_summary(anchor_date, daily, workouts, hrv, rhr, vo2, sleep)
    tripwires = _tripwires(freshness, anchor_date, weight_now, workouts, hrv, rhr)
    intervention = _intervention(tripwires)
    overall = _overall_status(freshness, tripwires)

    return _json_clean(
        {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "overall": overall,
            "goal": {
                "title": "Post-fast body-composition stint",
                "status": "partially configured",
                "start_date": WEIGHT_GOAL_START,
                "target_weight_band_kg": list(WEIGHT_BAND_KG),
                "intended_rate": "unconfirmed variant in playbook",
                "next_anchor": NEXT_DEXA_ANCHOR,
                "days_elapsed": max(0, (anchor_date - WEIGHT_GOAL_START).days),
                "open_decision": "Choose 3-week stint or -100 kcal/day variant; log whether it is still active.",
            },
            "freshness": freshness,
            "hero": {
                "as_of": anchor_date,
                "smoothed_weight_kg": _round(weight_now, 2),
                "target_weight_band_kg": list(WEIGHT_BAND_KG),
                "current_rate_kg_per_week": _round(weight_rate_week, 2),
                "intended_rate_kg_per_week": None,
                "projected_target_date": _project_weight_band_date(anchor_date, weight_now, weight_rate_week),
                "goal_delta_kg": _round(weight_delta_goal, 2),
                "latest_dexa": _dexa_snapshot(latest_dexa),
                "previous_dexa_delta": _dexa_delta(latest_dexa, previous_dexa),
                "estimate": estimate,
                "provenance": {
                    "smoothed_weight_kg": _provenance(
                        label="Eufy measured",
                        date=anchor_date,
                        provider="eufy Life via Apple Health / Health Auto Export",
                        raw_value=_latest_value(eufy_weight),
                        transformation="7-day rolling median by measurement date",
                        confidence="medium",
                    ),
                    "dexa_anchor": _provenance(
                        label="DEXA measured",
                        date=latest_dexa.get("scan_date") if latest_dexa else None,
                        provider=latest_dexa.get("provider") if latest_dexa else None,
                        raw_value=latest_dexa.get("body_fat_pct") if latest_dexa else None,
                        transformation="structured DEXA row, not merged with Eufy BIA",
                        confidence="high" if latest_dexa else "none",
                    ),
                    "estimate": estimate.get("provenance"),
                },
            },
            "body": composition,
            "performance": performance,
            "tripwires": tripwires,
            "intervention": intervention,
            "timeline": _timeline(anchor_date, eufy_weight, eufy_bf, dexa_rows, workouts, sleep),
            "modules": {
                "nutrition": {"state": "Add source", "latest": None},
                "bloodwork": {"state": "Add source", "latest": None},
                "genetics": {"state": "Add source", "latest": None},
                "experiments": {"state": "Add source", "latest": None},
            },
            "source_policy": {
                "body_fat": ["DEXA measured", "Eufy measured", "Estimated from DEXA + Eufy trend"],
                "rule": "Eufy BIA and DEXA values are separate series; only calibrated estimates combine them.",
            },
        }
    )


def _open_dashboard_conn(path: Path) -> duckdb.DuckDBPyConnection:
    if path.exists():
        try:
            return duckdb.connect(str(path), read_only=True)
        except duckdb.IOException:
            return duckdb.connect(str(path))
    conn = connect(path)
    load_schema(conn)
    return conn


def _rows(conn: duckdb.DuckDBPyConnection, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    result = conn.execute(sql, params)
    columns = [desc[0] for desc in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def _latest(conn: duckdb.DuckDBPyConnection, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    rows = _rows(conn, sql, params)
    return rows[0] if rows else None


def _body_series(conn: duckdb.DuckDBPyConnection, metric_type: str) -> list[dict[str, Any]]:
    return _rows(
        conn,
        """
        SELECT date, median(value) AS value, COUNT(*) AS samples, string_agg(DISTINCT source, ', ') AS source
        FROM body_comp_samples
        WHERE type = ? AND source = 'eufy Life'
        GROUP BY date
        ORDER BY date
        """,
        (metric_type,),
    )


def _daily_metrics(conn: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    return _rows(
        conn,
        """
        SELECT date,
               max(active_cal) AS active_cal,
               max(exercise_min) AS exercise_min,
               max(steps) AS steps,
               max(distance_km) AS distance_km,
               max(run_speed_kmh) AS run_speed_kmh,
               max(run_power_w) AS run_power_w,
               max(run_gct_ms) AS run_gct_ms,
               max(run_stride_cm) AS run_stride_cm,
               max(run_vert_osc_cm) AS run_vert_osc_cm,
               max(resp_rate) AS resp_rate
        FROM daily_metrics
        GROUP BY date
        ORDER BY date
        """,
    )


def _workout_daily(conn: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    return _rows(
        conn,
        """
        SELECT CAST(start_ts AS DATE) AS date,
               COUNT(*) AS workouts,
               SUM(duration_min) AS duration_min,
               SUM(distance_km) AS distance_km,
               SUM(calories) AS calories,
               MAX(duration_min) AS max_session_min,
               string_agg(DISTINCT type, ', ') AS types
        FROM workouts
        GROUP BY CAST(start_ts AS DATE)
        ORDER BY date
        """,
    )


def _hrv_daily(conn: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    return _rows(
        conn,
        """
        SELECT CAST(ts AS DATE) AS date, AVG(hrv_ms) AS hrv_ms, COUNT(*) AS samples
        FROM hrv_samples
        GROUP BY CAST(ts AS DATE)
        ORDER BY date
        """,
    )


def _sleep_daily(conn: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    return _rows(
        conn,
        """
        SELECT CAST(start_ts - INTERVAL 6 HOUR AS DATE) AS date,
               SUM(date_diff('minute', start_ts, end_ts)) AS sleep_min,
               COUNT(*) AS segments
        FROM sleep_segments
        WHERE value ILIKE '%Asleep%'
        GROUP BY CAST(start_ts - INTERVAL 6 HOUR AS DATE)
        ORDER BY date
        """,
    )


def _freshness(conn: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    rows = _rows(
        conn,
        """
        SELECT source, MAX(received_at) AS received_at, MAX(max_ts) AS max_ts
        FROM ingest_log
        WHERE source LIKE 'hae:%'
        GROUP BY source
        ORDER BY source
        """,
    )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    streams = []
    stale = []
    for row in rows:
        received_at = row.get("received_at")
        lag_hours = None
        if isinstance(received_at, datetime):
            lag_hours = (now - received_at).total_seconds() / 3600
        item = {
            "source": row.get("source"),
            "received_at": received_at,
            "max_ts": row.get("max_ts"),
            "lag_hours": _round(lag_hours, 2),
            "stale": lag_hours is None or lag_hours > MAX_HAE_LAG_HOURS,
        }
        streams.append(item)
        if item["stale"]:
            stale.append(item)

    if not rows:
        return {
            "ok": False,
            "state": "Data needed",
            "stream_count": 0,
            "stale_count": 1,
            "max_lag_hours": None,
            "streams": [],
            "stale": [{"source": "hae:*", "lag_hours": None}],
        }

    max_lag = max((s.get("lag_hours") or 0 for s in streams), default=None)
    return {
        "ok": not stale,
        "state": "Fresh" if not stale else "Stale",
        "stream_count": len(streams),
        "stale_count": len(stale),
        "max_lag_hours": _round(max_lag, 2),
        "streams": streams,
        "stale": stale,
    }


def _composition_summary(
    latest_dexa: dict[str, Any] | None,
    previous_dexa: dict[str, Any] | None,
    weight_now: float | None,
    bf_now: float | None,
    lean_now: float | None,
    estimate: dict[str, Any],
) -> dict[str, Any]:
    latest_date = latest_dexa.get("scan_date") if latest_dexa else None
    metrics = [
        {
            "key": "weight_trend",
            "label": "Weight trend",
            "value": _round(weight_now, 2),
            "unit": "kg",
            "source_label": "Eufy measured",
            "provenance": _provenance("Eufy measured", latest_date, "eufy Life", weight_now, "7-day rolling median", "medium"),
        },
        {
            "key": "dexa_bf",
            "label": "DEXA body fat",
            "value": _round(latest_dexa.get("body_fat_pct") if latest_dexa else None, 1),
            "unit": "%",
            "source_label": "DEXA measured",
            "provenance": _dexa_metric_provenance(latest_dexa, "body_fat_pct", "structured DEXA body-fat percentage"),
        },
        {
            "key": "estimated_bf",
            "label": "Estimated current body fat",
            "value": estimate.get("range_label"),
            "unit": "%",
            "source_label": "Estimated from DEXA + Eufy trend",
            "provenance": estimate.get("provenance"),
        },
        {
            "key": "dexa_lean",
            "label": "DEXA lean + BMC",
            "value": _round(latest_dexa.get("lean_bmc_kg") if latest_dexa else None, 2),
            "unit": "kg",
            "source_label": "DEXA measured",
            "provenance": _dexa_metric_provenance(latest_dexa, "lean_bmc_kg", "structured DEXA lean plus bone mineral content"),
        },
        {
            "key": "estimated_lean_plus_bone",
            "label": "Estimated lean + bone mass",
            "value": _round(estimate.get("lean_plus_bone_kg"), 2),
            "unit": "kg",
            "source_label": "Estimated from DEXA + Eufy trend",
            "provenance": estimate.get("provenance"),
        },
        {
            "key": "appendicular_lean",
            "label": "Appendicular lean + BMC",
            "value": _round(latest_dexa.get("appendicular_lean_bmc_kg") if latest_dexa else None, 2),
            "unit": "kg",
            "source_label": "DEXA measured",
            "provenance": _dexa_metric_provenance(latest_dexa, "appendicular_lean_bmc_kg", "structured DEXA appendicular lean plus BMC"),
        },
        {
            "key": "vat",
            "label": "Visceral adipose tissue",
            "value": _round(latest_dexa.get("vat_mass_g") if latest_dexa else None, 0),
            "unit": "g",
            "source_label": "DEXA measured",
            "provenance": _dexa_metric_provenance(latest_dexa, "vat_mass_g", "structured DEXA VAT mass"),
        },
        {
            "key": "android_gynoid",
            "label": "Android/gynoid ratio",
            "value": _round(latest_dexa.get("android_gynoid_ratio") if latest_dexa else None, 2),
            "unit": "",
            "source_label": "DEXA measured",
            "provenance": _dexa_metric_provenance(latest_dexa, "android_gynoid_ratio", "structured DEXA regional ratio"),
        },
        {
            "key": "bone_density",
            "label": "Bone density",
            "value": _round(latest_dexa.get("bmd_total_g_cm2") if latest_dexa else None, 3),
            "unit": "g/cm2",
            "source_label": "DEXA measured",
            "provenance": _dexa_metric_provenance(latest_dexa, "bmd_total_g_cm2", "structured DEXA total BMD"),
        },
        {
            "key": "waist",
            "label": "Waist",
            "value": None,
            "unit": "",
            "source_label": "Add source",
            "provenance": _provenance("User entered", None, None, None, "No waist source connected", "none"),
        },
    ]
    return {
        "latest_dexa_date": latest_date,
        "dexa_delta": _dexa_delta(latest_dexa, previous_dexa),
        "metrics": metrics,
    }


def _performance_summary(
    anchor_date: date,
    daily: list[dict[str, Any]],
    workouts: list[dict[str, Any]],
    hrv: list[dict[str, Any]],
    rhr: list[dict[str, Any]],
    vo2: dict[str, Any] | None,
    sleep: list[dict[str, Any]],
) -> dict[str, Any]:
    daily_7 = _window_rows(daily, anchor_date, 7)
    workout_7 = _window_rows(workouts, anchor_date, 7)
    hrv_7 = _window_rows(hrv, anchor_date, 7)
    rhr_7 = _window_rows(rhr, anchor_date, 7)
    sleep_7 = _window_rows(sleep, anchor_date, 7)

    exercise_min = _sum_field(daily_7, "exercise_min")
    distance_km = _sum_field(daily_7, "distance_km") or _sum_field(workout_7, "distance_km")
    steps = _sum_field(daily_7, "steps")
    active_cal = _sum_field(daily_7, "active_cal")
    workout_minutes = _sum_field(workout_7, "duration_min")
    hrv_med = _median_values([r.get("hrv_ms") for r in hrv_7])
    rhr_med = _median_values([r.get("resting_hr") for r in rhr_7])
    sleep_med = _median_values([r.get("sleep_min") for r in sleep_7])

    return {
        "anchor_date": anchor_date,
        "metrics": [
            _metric("Weekly exercise", exercise_min, "min", "Apple Health", daily_7[-1].get("date") if daily_7 else None, "sum of daily exercise minutes over 7 days", "medium"),
            _metric("Workout duration", workout_minutes, "min", "Apple Watch workouts", workout_7[-1].get("date") if workout_7 else None, "sum of imported workouts over 7 days", "medium"),
            _metric("Running/walking distance", distance_km, "km", "Apple Health", daily_7[-1].get("date") if daily_7 else None, "sum of distance streams over 7 days", "low" if distance_km is None else "medium"),
            _metric("Steps", steps, "steps", "Apple Health", daily_7[-1].get("date") if daily_7 else None, "sum of step count over 7 days", "medium"),
            _metric("Active energy", active_cal, "kcal", "Apple Health", daily_7[-1].get("date") if daily_7 else None, "sum of active energy over 7 days", "medium"),
            _metric("VO2 max", vo2.get("vo2max") if vo2 else None, "mL/kg/min", "Apple Health cardio fitness", vo2.get("date") if vo2 else None, "latest Apple estimate; not lab measured", "medium" if vo2 else "none"),
            _metric("Resting HR", rhr_med, "bpm", "Apple Health", rhr_7[-1].get("date") if rhr_7 else None, "7-day median resting heart rate", "medium"),
            _metric("HRV", hrv_med, "ms", "Apple Watch SDNN", hrv_7[-1].get("date") if hrv_7 else None, "7-day median of daily SDNN averages", "medium"),
            _metric("Sleep", sleep_med / 60 if sleep_med is not None else None, "h", "Apple Watch sleep", sleep_7[-1].get("date") if sleep_7 else None, "7-day median asleep duration", "low" if not sleep_7 else "medium"),
            _metric("Strength progression", None, "", "Add source", None, "strength log not connected", "none"),
        ],
    }


def _tripwires(
    freshness: dict[str, Any],
    anchor_date: date,
    weight_now: float | None,
    workouts: list[dict[str, Any]],
    hrv: list[dict[str, Any]],
    rhr: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    items = []
    if freshness.get("ok"):
        items.append(
            _tripwire(
                "data-freshness",
                "Live Health Auto Export fresh",
                "Resolved",
                "low",
                "All HAE streams received within configured freshness window.",
                f"max lag {freshness.get('max_lag_hours')} h; {freshness.get('stream_count')} streams",
                "Health Auto Export ingest_log",
                freshness.get("streams", [])[-1].get("received_at") if freshness.get("streams") else None,
                "No action.",
                "stale_count remains 0",
            )
        )
    else:
        items.append(
            _tripwire(
                "data-freshness",
                "Live Health Auto Export stale",
                "Triggered",
                "high",
                f"Any HAE source older than {MAX_HAE_LAG_HOURS} h or no HAE payloads.",
                f"{freshness.get('stale_count')} stale stream(s)",
                "Health Auto Export ingest_log",
                None,
                "Open Health Auto Export, charge/unlock phone, then retry ingest.",
                "all HAE streams fresh again",
            )
        )

    low, high = WEIGHT_BAND_KG
    if weight_now is None:
        state = "Data needed"
        severity = "medium"
        evidence = "No Eufy 7-day weight trend available."
        action = "Restore Eufy weight stream."
    elif weight_now < low or weight_now > high:
        state = "Triggered"
        severity = "high"
        evidence = f"7-day Eufy weight median {weight_now:.2f} kg outside {low:.1f}-{high:.1f} kg."
        action = "Review deficit; stop if below floor, otherwise resolve the unconfirmed stint variant."
    else:
        state = "Resolved"
        severity = "low"
        evidence = f"7-day Eufy weight median {weight_now:.2f} kg inside {low:.1f}-{high:.1f} kg."
        action = "Maintain current plan."
    items.append(
        _tripwire(
            "stint-weight-band",
            "Stint weight floor/ceiling",
            state,
            severity,
            "Eufy weight 7-day rolling mean outside 70.5-71.5 kg.",
            evidence,
            "eufy Life body_comp_samples",
            anchor_date,
            action,
            "7-day rolling mean returns inside 70.5-71.5 kg",
        )
    )

    load_item = _training_load_tripwire(anchor_date, workouts)
    if load_item:
        items.append(load_item)
    hrv_item = _hrv_tripwire(anchor_date, hrv)
    if hrv_item:
        items.append(hrv_item)
    rhr_item = _rhr_tripwire(anchor_date, rhr)
    if rhr_item:
        items.append(rhr_item)
    return items


def _training_load_tripwire(anchor_date: date, workouts: list[dict[str, Any]]) -> dict[str, Any] | None:
    last_7 = _window_rows(workouts, anchor_date, 7)
    prev_21 = [r for r in workouts if anchor_date - timedelta(days=28) <= r.get("date") < anchor_date - timedelta(days=7)]
    max_session = max((_float(r.get("max_session_min")) or 0 for r in last_7), default=0)
    acute = (_sum_field(last_7, "duration_min") or 0) / 7
    chronic = (_sum_field(prev_21, "duration_min") or 0) / 21 if prev_21 else None
    acwr = acute / chronic if chronic and chronic > 0 else None

    if max_session > 120:
        return _tripwire(
            "long-session-recovery",
            "Long-session recovery",
            "Triggered",
            "medium",
            "Single workout day above 120 min.",
            f"max session {max_session:.0f} min in the last 7 days",
            "Apple Watch workouts",
            anchor_date,
            "Expect next-day HRV/RHR dip; do not stack intensity.",
            "no >120 min session in the current review window",
        )
    if acwr is None:
        return _tripwire(
            "training-load-increase",
            "Training-load increase",
            "Data needed",
            "medium",
            "ACWR flags above 1.5 using workout duration until TRIMP is populated.",
            "insufficient prior workout duration",
            "Apple Watch workouts",
            anchor_date,
            "Keep importing workouts; compute TRIMP when HR calibration is ready.",
            "28-day workout history available",
        )
    if acwr > 1.5:
        return _tripwire(
            "training-load-increase",
            "Training-load increase",
            "Watch",
            "medium",
            "ACWR > 1.5 from playbook C2.",
            f"duration ACWR {acwr:.2f}",
            "Apple Watch workouts",
            anchor_date,
            "Avoid adding intensity until acute load normalizes.",
            "ACWR <= 1.5",
        )
    return _tripwire(
        "training-load-increase",
        "Training-load increase",
        "Resolved",
        "low",
        "ACWR > 1.5 from playbook C2.",
        f"duration ACWR {acwr:.2f}",
        "Apple Watch workouts",
        anchor_date,
        "No action.",
        "ACWR <= 1.5",
    )


def _hrv_tripwire(anchor_date: date, hrv: list[dict[str, Any]]) -> dict[str, Any] | None:
    recent = _window_rows(hrv, anchor_date, 35)
    if len(recent) < 14:
        return _tripwire(
            "hrv-strain",
            "HRV strain",
            "Data needed",
            "medium",
            "HRV 7-day mean below 28-day baseline minus SWC for 3 consecutive days.",
            "fewer than 14 HRV days available",
            "Apple Watch SDNN",
            anchor_date,
            "Keep watch worn overnight.",
            "28-day baseline available",
        )
    baseline_rows = [r for r in recent if r.get("date") <= anchor_date - timedelta(days=7)]
    last3 = [r for r in recent if r.get("date") > anchor_date - timedelta(days=3)]
    vals = [_float(r.get("hrv_ms")) for r in baseline_rows]
    vals = [v for v in vals if v is not None and v > 0]
    if len(vals) < 7 or len(last3) < 3:
        return None
    base = sum(vals) / len(vals)
    swc = 0.5 * pstdev(vals) if len(vals) > 1 else 0
    threshold = base - swc
    last_vals = [_float(r.get("hrv_ms")) for r in last3]
    fired = all(v is not None and v < threshold for v in last_vals)
    return _tripwire(
        "hrv-strain",
        "HRV strain",
        "Triggered" if fired else "Resolved",
        "medium" if fired else "low",
        "HRV 7-day mean below 28-day baseline minus SWC for 3 consecutive days.",
        f"baseline {base:.1f} ms, SWC {swc:.1f}, last values {', '.join(f'{v:.1f}' for v in last_vals if v is not None)} ms",
        "Apple Watch SDNN",
        anchor_date,
        "No intensity; deload check." if fired else "No action.",
        "HRV returns within baseline band for 3 days",
    )


def _rhr_tripwire(anchor_date: date, rhr: list[dict[str, Any]]) -> dict[str, Any] | None:
    recent = _window_rows(rhr, anchor_date, 35)
    if len(recent) < 14:
        return _tripwire(
            "rhr-strain",
            "Resting HR strain",
            "Data needed",
            "medium",
            "RHR elevated versus 28-day baseline for 3 days.",
            "fewer than 14 RHR days available",
            "Apple Health resting_hr",
            anchor_date,
            "Keep watch worn overnight.",
            "28-day baseline available",
        )
    baseline_rows = [r for r in recent if r.get("date") <= anchor_date - timedelta(days=7)]
    last3 = [r for r in recent if r.get("date") > anchor_date - timedelta(days=3)]
    vals = [_float(r.get("resting_hr")) for r in baseline_rows]
    vals = [v for v in vals if v is not None]
    if len(vals) < 7 or len(last3) < 3:
        return None
    base = sum(vals) / len(vals)
    swc = 0.5 * pstdev(vals) if len(vals) > 1 else 0
    threshold = base + max(5, swc)
    last_vals = [_float(r.get("resting_hr")) for r in last3]
    fired = all(v is not None and v > threshold for v in last_vals)
    return _tripwire(
        "rhr-strain",
        "Resting HR strain",
        "Triggered" if fired else "Resolved",
        "medium" if fired else "low",
        "RHR above personal baseline threshold for 3 days.",
        f"baseline {base:.1f} bpm, threshold {threshold:.1f}, last values {', '.join(f'{v:.0f}' for v in last_vals if v is not None)} bpm",
        "Apple Health resting_hr",
        anchor_date,
        "Check illness/recovery; avoid intensity." if fired else "No action.",
        "RHR returns within baseline band for 3 days",
    )


def _intervention(tripwires: list[dict[str, Any]]) -> dict[str, Any]:
    priority = {"high": 3, "medium": 2, "low": 1}
    actionable = [t for t in tripwires if t.get("state") in {"Triggered", "Watch", "Data needed"}]
    if not actionable:
        return {
            "title": "Maintain the current plan; no intervention required.",
            "why": "No active high-priority tripwire is currently triggered.",
            "supporting_measurements": [],
            "confidence": "medium",
            "review_date": None,
            "source_tripwire": None,
        }
    selected = sorted(actionable, key=lambda t: (priority.get(t.get("severity", "low"), 0), t.get("state") == "Triggered"), reverse=True)[0]
    return {
        "title": selected.get("recommended_action"),
        "why": selected.get("title"),
        "supporting_measurements": [selected.get("evidence")],
        "confidence": "high" if selected.get("state") == "Triggered" else "medium",
        "review_date": selected.get("review_date"),
        "source_tripwire": selected.get("id"),
    }


def _overall_status(freshness: dict[str, Any], tripwires: list[dict[str, Any]]) -> dict[str, str]:
    if not freshness.get("ok"):
        return {"state": "Insufficient data", "tone": "amber", "phrase": "Insufficient data"}
    if any(t.get("state") == "Triggered" and t.get("severity") == "high" for t in tripwires):
        return {"state": "Action required", "tone": "coral", "phrase": "Action required"}
    if any(t.get("state") in {"Triggered", "Watch", "Data needed"} for t in tripwires):
        return {"state": "Watch", "tone": "amber", "phrase": "Watch"}
    return {"state": "On track", "tone": "green", "phrase": "On track"}


def _timeline(
    anchor_date: date,
    eufy_weight: list[dict[str, Any]],
    eufy_bf: list[dict[str, Any]],
    dexa_rows: list[dict[str, Any]],
    workouts: list[dict[str, Any]],
    sleep: list[dict[str, Any]],
) -> dict[str, Any]:
    start = anchor_date - timedelta(days=59)
    return {
        "start": start,
        "end": anchor_date,
        "series": {
            "weight": _series_slice(eufy_weight, start, anchor_date, "value", 2),
            "eufy_body_fat": _series_slice(eufy_bf, start, anchor_date, "value", 1),
            "sleep_hours": [
                {"date": r.get("date"), "value": _round((_float(r.get("sleep_min")) or 0) / 60, 2)}
                for r in sleep
                if start <= r.get("date") <= anchor_date and r.get("sleep_min") is not None
            ],
        },
        "events": [
            {"date": r.get("scan_date"), "type": "DEXA", "label": f"DEXA {r.get('body_fat_pct')}%"}
            for r in dexa_rows
            if start <= r.get("scan_date") <= anchor_date
        ]
        + [
            {"date": r.get("date"), "type": "Workout", "label": f"{_round(r.get('duration_min'), 0)} min"}
            for r in workouts
            if start <= r.get("date") <= anchor_date and (_float(r.get("duration_min")) or 0) > 0
        ],
    }


def _calibration(dexa_rows: list[dict[str, Any]], eufy_bf: list[dict[str, Any]]) -> dict[str, Any]:
    offsets = []
    for scan in dexa_rows:
        scan_date = scan.get("scan_date")
        dexa_bf = _float(scan.get("body_fat_pct"))
        eufy = _median_between(eufy_bf, scan_date - timedelta(days=3), scan_date + timedelta(days=3)) if scan_date else None
        if dexa_bf is not None and eufy is not None:
            offsets.append({"date": scan_date, "offset": dexa_bf - eufy, "dexa_bf": dexa_bf, "eufy_bf": eufy})
    latest = offsets[-1] if offsets else None
    spread = pstdev([o["offset"] for o in offsets]) if len(offsets) >= 2 else None
    return {
        "latest_offset": _round(latest.get("offset") if latest else None, 2),
        "latest_offset_date": latest.get("date") if latest else None,
        "latest_eufy_near_scan": _round(latest.get("eufy_bf") if latest else None, 1),
        "count": len(offsets),
        "offset_sd": _round(spread, 2),
        "offsets": offsets,
    }


def _dexa_anchored_estimate(weight_now: float | None, bf_now: float | None, calibration: dict[str, Any]) -> dict[str, Any]:
    offset = _float(calibration.get("latest_offset"))
    if weight_now is None or bf_now is None or offset is None:
        return {
            "available": False,
            "range_label": "Add source",
            "confidence": "none",
            "provenance": _provenance("Estimated from DEXA + Eufy trend", None, None, None, "Missing current Eufy trend or DEXA calibration", "none"),
        }
    estimate = bf_now + offset
    half_width = max(0.8, _float(calibration.get("offset_sd")) or 1.2)
    low = max(0, estimate - half_width)
    high = estimate + half_width
    fat_mass = weight_now * estimate / 100
    return {
        "available": True,
        "body_fat_pct_mid": _round(estimate, 1),
        "body_fat_pct_range": [_round(low, 1), _round(high, 1)],
        "range_label": f"{low:.1f}-{high:.1f}",
        "fat_mass_kg": _round(fat_mass, 2),
        "lean_plus_bone_kg": _round(weight_now - fat_mass, 2),
        "confidence": "medium" if calibration.get("count", 0) >= 2 else "low",
        "provenance": _provenance(
            "Estimated from DEXA + Eufy trend",
            calibration.get("latest_offset_date"),
            "BodyStats DEXA + eufy Life",
            f"Eufy BF 7d {bf_now:.1f}%, offset {offset:+.2f} pp",
            "latest DEXA minus median Eufy BF within +/- 3 days; offset applied to current Eufy 7-day median",
            "medium" if calibration.get("count", 0) >= 2 else "low",
        ),
        "calibration": calibration,
    }


def _dexa_snapshot(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "scan_date": row.get("scan_date"),
        "provider": row.get("provider"),
        "weight_kg": _round(row.get("weight_kg"), 2),
        "body_fat_pct": _round(row.get("body_fat_pct"), 1),
        "fat_mass_kg": _round(row.get("fat_mass_kg"), 2),
        "lean_bmc_kg": _round(row.get("lean_bmc_kg"), 2),
        "vat_mass_g": _round(row.get("vat_mass_g"), 0),
    }


def _dexa_delta(latest: dict[str, Any] | None, previous: dict[str, Any] | None) -> dict[str, Any] | None:
    if not latest or not previous:
        return None
    return {
        "from_date": previous.get("scan_date"),
        "to_date": latest.get("scan_date"),
        "weight_kg": _round(_delta(latest.get("weight_kg"), previous.get("weight_kg")), 2),
        "body_fat_pct": _round(_delta(latest.get("body_fat_pct"), previous.get("body_fat_pct")), 1),
        "fat_mass_kg": _round(_delta(latest.get("fat_mass_kg"), previous.get("fat_mass_kg")), 2),
        "lean_bmc_kg": _round(_delta(latest.get("lean_bmc_kg"), previous.get("lean_bmc_kg")), 2),
        "vat_mass_g": _round(_delta(latest.get("vat_mass_g"), previous.get("vat_mass_g")), 0),
    }


def _project_weight_band_date(anchor_date: date, weight_now: float | None, rate_week: float | None) -> str | None:
    if weight_now is None:
        return None
    low, high = WEIGHT_BAND_KG
    if low <= weight_now <= high:
        return anchor_date.isoformat()
    if not rate_week or abs(rate_week) < 0.01:
        return None
    target = high if weight_now > high else low
    days = (target - weight_now) / (rate_week / 7)
    if days < 0 or days > 365:
        return None
    return (anchor_date + timedelta(days=round(days))).isoformat()


def _metric(label: str, value: Any, unit: str, provider: str, observed_date: Any, transformation: str, confidence: str) -> dict[str, Any]:
    return {
        "label": label,
        "value": _round(value, 1),
        "unit": unit,
        "source_label": provider if provider != "Add source" else "Add source",
        "provenance": _provenance(provider, observed_date, provider, value, transformation, confidence),
    }


def _tripwire(
    item_id: str,
    title: str,
    state: str,
    severity: str,
    rule: str,
    evidence: str,
    sources: str,
    recency: Any,
    action: str,
    resolution: str,
) -> dict[str, Any]:
    review_date = None
    if isinstance(recency, date):
        review_date = recency + timedelta(days=7)
    return {
        "id": item_id,
        "title": title,
        "state": state,
        "severity": severity,
        "rule": rule,
        "evidence": evidence,
        "sources": sources,
        "data_recency": recency,
        "recommended_action": action,
        "triggered_date": recency if state in {"Triggered", "Watch", "Data needed"} else None,
        "review_date": review_date,
        "resolution_condition": resolution,
    }


def _provenance(label: str, date: Any, provider: Any, raw_value: Any, transformation: str, confidence: str) -> dict[str, Any]:
    return {
        "label": label,
        "date": date,
        "device_provider": provider,
        "raw_value": raw_value,
        "transformation": transformation,
        "confidence": confidence,
    }


def _dexa_metric_provenance(row: dict[str, Any] | None, key: str, transformation: str) -> dict[str, Any]:
    return _provenance(
        "DEXA measured",
        row.get("scan_date") if row else None,
        row.get("provider") if row else None,
        row.get(key) if row else None,
        transformation,
        "high" if row and row.get(key) is not None else "none",
    )


def _max_date(*series: list[dict[str, Any]]) -> date | None:
    values = []
    for rows in series:
        for row in rows:
            value = row.get("date") or row.get("scan_date")
            if isinstance(value, datetime):
                value = value.date()
            if isinstance(value, date):
                values.append(value)
    return max(values) if values else None


def _window_rows(rows: list[dict[str, Any]], end: date, days: int) -> list[dict[str, Any]]:
    start = end - timedelta(days=days - 1)
    return [r for r in rows if isinstance(r.get("date"), date) and start <= r["date"] <= end]


def _window_median(rows: list[dict[str, Any]], end: date, days: int) -> float | None:
    return _median_values([r.get("value") for r in _window_rows(rows, end, days)])


def _median_between(rows: list[dict[str, Any]], start: date, end: date) -> float | None:
    return _median_values([r.get("value") for r in rows if isinstance(r.get("date"), date) and start <= r["date"] <= end])


def _median_values(values: list[Any]) -> float | None:
    nums = [_float(v) for v in values]
    nums = [v for v in nums if v is not None]
    return float(median(nums)) if nums else None


def _nearest_value(rows: list[dict[str, Any]], target: date, max_days: int) -> float | None:
    candidates = []
    for row in rows:
        row_date = row.get("date")
        if not isinstance(row_date, date):
            continue
        delta = abs((row_date - target).days)
        if delta <= max_days:
            candidates.append((delta, row_date, row.get("value")))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1]))
    return _float(candidates[0][2])


def _latest_value(rows: list[dict[str, Any]]) -> Any:
    if not rows:
        return None
    return rows[-1].get("value")


def _sum_field(rows: list[dict[str, Any]], field: str) -> float | None:
    total = 0.0
    seen = False
    for row in rows:
        value = _float(row.get(field))
        if value is None:
            continue
        total += value
        seen = True
    return total if seen else None


def _series_slice(rows: list[dict[str, Any]], start: date, end: date, field: str, digits: int) -> list[dict[str, Any]]:
    series = []
    for row in rows:
        row_date = row.get("date")
        value = _float(row.get(field))
        if isinstance(row_date, date) and start <= row_date <= end and value is not None:
            series.append({"date": row_date, "value": _round(value, digits)})
    return series


def _delta(a: Any, b: Any) -> float | None:
    left = _float(a)
    right = _float(b)
    if left is None or right is None:
        return None
    return left - right


def _float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(result):
        return None
    return result


def _round(value: Any, digits: int) -> float | None:
    number = _float(value)
    if number is None:
        return None
    if digits <= 0:
        return float(round(number))
    return round(number, digits)


def _json_clean(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_clean(v) for v in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value
