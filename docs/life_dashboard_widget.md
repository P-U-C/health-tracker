# Life Dashboard Widget

The life dashboard consumes a static snapshot:

`~/.local/state/health-tracker-widget.json`

Generate it:

```bash
cd /home/ubuntu/health
uv run --quiet python -m jobs.widget_snapshot --db data/health.duckdb --out ~/.local/state/health-tracker-widget.json
```

Install the console module:

```bash
cp /home/ubuntu/health/ops/console/health.py /home/ubuntu/ops-state/modules/health.py
```

Expected snapshot shape:

```json
{
  "generated_at": "2026-09-16T22:00:00Z",
  "status": "ok",
  "summary": {
    "weight_kg": 72.4,
    "body_fat_pct": 16.7,
    "latest_dexa": "2026-08-31",
    "hae_stream_count": 8,
    "hae_stale_count": 0
  },
  "items": [
    {"status": "ok", "title": "live health pipe fresh", "detail": "8 streams, latest payload 0.2 h ago"}
  ]
}
```

The ops console module must never call an LLM. It only reads the snapshot.
