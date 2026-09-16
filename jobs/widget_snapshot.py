from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.schema import DEFAULT_DB, connect, load_schema, table_count
from jobs.staleness_monitor import check_staleness

DEFAULT_OUT = Path.home() / ".local" / "state" / "health-tracker-widget.json"


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _latest(conn, sql: str) -> dict[str, Any] | None:
    row = conn.execute(sql).fetchone()
    if not row:
        return None
    columns = [desc[0] for desc in conn.description]
    return {columns[i]: row[i] for i in range(len(columns))}


def build_snapshot(db_path: str | Path = DEFAULT_DB) -> dict[str, Any]:
    staleness = check_staleness(db_path)
    conn = connect(db_path)
    try:
        load_schema(conn)
        latest_weight = _latest(
            conn,
            """
            SELECT date, value AS weight_kg, source
            FROM body_comp_samples
            WHERE type = 'weight_kg'
            ORDER BY date DESC
            LIMIT 1
            """,
        )
        latest_body_fat = _latest(
            conn,
            """
            SELECT date, value AS body_fat_pct, source
            FROM body_comp_samples
            WHERE type = 'body_fat_pct'
            ORDER BY date DESC
            LIMIT 1
            """,
        )
        latest_daily = _latest(
            conn,
            """
            SELECT date, steps, active_cal, exercise_min, stand_min
            FROM daily_metrics
            ORDER BY date DESC
            LIMIT 1
            """,
        )
        latest_hrv = _latest(
            conn,
            """
            SELECT ts, hrv_ms
            FROM hrv_samples
            ORDER BY ts DESC
            LIMIT 1
            """,
        )
        latest_resting_hr = _latest(
            conn,
            """
            SELECT date, resting_hr
            FROM resting_hr
            ORDER BY date DESC
            LIMIT 1
            """,
        )
        dexa = _latest(
            conn,
            """
            SELECT scan_date, body_fat_pct, fat_mass_kg, lean_bmc_kg, vat_mass_g
            FROM dexa_scans
            ORDER BY scan_date DESC
            LIMIT 1
            """,
        )
        latest_ingest = conn.execute("SELECT MAX(received_at) FROM ingest_log").fetchone()[0]
        dexa_rows = table_count(conn, "dexa_scans")
    finally:
        conn.close()

    now = datetime.now(timezone.utc).replace(microsecond=0)
    generated_at = now.isoformat().replace("+00:00", "Z")
    status = "ok" if staleness.get("ok") else "bad"
    if status == "ok" and not latest_weight:
        status = "warn"

    stream_count = int(staleness.get("stream_count", 0) or 0)
    stale_count = int(staleness.get("stale_count", 0) or 0)
    max_lag = max((float(s.get("lag_hours") or 0) for s in staleness.get("streams", [])), default=None)

    items = []
    if stale_count:
        items.append({
            "status": "bad",
            "title": "live health pipe stale",
            "detail": f"{stale_count} stale stream(s); open Health Auto Export or charge/unlock phone",
            "needs_you": True,
        })
    else:
        items.append({
            "status": "ok",
            "title": "live health pipe fresh",
            "detail": f"{stream_count} streams; max ingest lag {max_lag:.2f} h" if max_lag is not None else "no lag reported",
        })

    if dexa:
        items.append({
            "status": "ok",
            "title": f"latest DEXA {dexa['scan_date']}",
            "detail": f"{dexa['body_fat_pct']}% BF, VAT {dexa['vat_mass_g']} g",
        })

    summary = {
        "weight_kg": round(float(latest_weight["weight_kg"]), 2) if latest_weight else None,
        "weight_date": _iso(latest_weight["date"]) if latest_weight else None,
        "body_fat_pct": round(float(latest_body_fat["body_fat_pct"]), 2) if latest_body_fat else None,
        "body_fat_date": _iso(latest_body_fat["date"]) if latest_body_fat else None,
        "latest_dexa": _iso(dexa["scan_date"]) if dexa else None,
        "dexa_rows": dexa_rows,
        "hae_stream_count": stream_count,
        "hae_stale_count": stale_count,
        "latest_ingest": _iso(latest_ingest),
    }

    return {
        "generated_at": generated_at,
        "status": status,
        "summary": summary,
        "latest": {
            "daily_metrics": {k: _iso(v) for k, v in (latest_daily or {}).items()},
            "hrv": {k: _iso(v) for k, v in (latest_hrv or {}).items()},
            "resting_hr": {k: _iso(v) for k, v in (latest_resting_hr or {}).items()},
            "dexa": {k: _iso(v) for k, v in (dexa or {}).items()},
        },
        "items": items,
    }


def write_snapshot(snapshot: dict[str, Any], out_path: str | Path = DEFAULT_OUT) -> Path:
    out = Path(out_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a static health widget snapshot for the life dashboard.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    out = write_snapshot(build_snapshot(args.db), args.out)
    print(str(out))


if __name__ == "__main__":
    main()
