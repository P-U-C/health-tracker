from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from core.schema import DEFAULT_DB, connect, load_schema
from jobs.push import push_line

MAX_LAG_HOURS = 36


def check_staleness(db_path: str | Path = DEFAULT_DB, max_lag_hours: int = MAX_LAG_HOURS, notify: bool = False) -> dict[str, object]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    conn = connect(db_path)
    try:
        load_schema(conn)
        rows = conn.execute(
            """
            SELECT source, MAX(received_at) AS received_at, MAX(max_ts) AS max_ts
            FROM ingest_log
            WHERE source LIKE 'hae:%'
            GROUP BY source
            ORDER BY source
            """
        ).fetchall()
    finally:
        conn.close()

    streams = []
    stale = []
    for source, received_at, max_ts in rows:
        lag_hours = (now - received_at).total_seconds() / 3600
        item = {
            "source": source,
            "received_at": received_at.isoformat(),
            "max_ts": str(max_ts) if max_ts is not None else None,
            "lag_hours": round(lag_hours, 2),
            "stale": lag_hours > max_lag_hours,
        }
        streams.append(item)
        if item["stale"]:
            stale.append(item)

    if not rows:
        message = "health HAE stale: no live HAE payloads recorded; open Health Auto Export or configure phone automation."
        pushed = push_line(message) if notify else {}
        return {"ok": False, "stream_count": 0, "stale_count": 1, "stale": [{"source": "hae:*", "lag_hours": None}], "pushed": pushed}

    pushed = {}
    if stale and notify:
        worst = max(stale, key=lambda item: item["lag_hours"] or 0)
        pushed = push_line(f"health HAE stale: {len(stale)} stream(s), worst {worst['source']} lag {worst['lag_hours']} h; open HAE/charge phone.")

    return {"ok": not stale, "stream_count": len(streams), "stale_count": len(stale), "streams": streams, "stale": stale, "pushed": pushed}


def main() -> None:
    parser = argparse.ArgumentParser(description="Alert when Health Auto Export streams stop arriving.")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--max-lag-hours", type=int, default=MAX_LAG_HOURS)
    parser.add_argument("--notify", action="store_true")
    args = parser.parse_args()
    result = check_staleness(args.db, args.max_lag_hours, args.notify)
    print(json.dumps(result, indent=2))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
