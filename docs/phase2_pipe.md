# Phase 2 Pipe

## Local API

```bash
cd /home/ubuntu/health
export HEALTH_DB=/home/ubuntu/health/data/health.duckdb
export HEALTH_INGEST_TOKEN='<random secret in vault/env, never committed>'
make api
```

Health Auto Export sends:

```http
POST /ingest/hae
Authorization: Bearer <HEALTH_INGEST_TOKEN>
Content-Type: application/json
```

Expected payload root:

```json
{"data":{"metrics":[{"name":"heart_rate","units":"bpm","data":[]}],"workouts":[]}}
```

Response includes `rows_seen`, `inserted`, `updated`, `rows_upserted`, and per-stream counts.

## Cloudflare Tunnel

Stable tunnel target:

```bash
cloudflared tunnel route dns <tunnel-name> health.<domain>
cloudflared tunnel run <tunnel-name>
```

Tunnel service config:

```yaml
ingress:
  - hostname: health.<domain>
    service: http://127.0.0.1:8026
  - service: http_status:404
```

Do not expose `/ingest/hae` without `HEALTH_INGEST_TOKEN`.

## Health Auto Export

Automation:

- Method: `POST`
- URL: `https://health.<domain>/ingest/hae`
- Header: `Authorization: Bearer <HEALTH_INGEST_TOKEN>`
- Metrics: heart rate, HRV, resting HR, VO2max, SpO2, sleep, weight, body fat, lean mass, steps, gait, stairs, respiratory rate, daylight, energy, exercise, stand time, flights, physical effort, running form, audio exposure
- Workouts: enabled
- Cadence: hourly if iOS allows; daily is insufficient for the 36 h staleness rule

## Fresh Apple Health Backfill

```bash
cd /home/ubuntu/health
uv run python -m ingest.apple_export_xml /path/to/export.xml --db data/health.duckdb
```

Merge rule: rows at or before each stream's existing max timestamp are ignored. Existing package rows are not overwritten.

## Staleness Monitor

```bash
cd /home/ubuntu/health
uv run python -m jobs.staleness_monitor --db data/health.duckdb --notify
```

Cron candidate:

```cron
17 * * * * cd /home/ubuntu/health && /home/ubuntu/.local/bin/uv run --quiet python -m jobs.staleness_monitor --db data/health.duckdb --notify >> /home/ubuntu/logs/health-staleness.log 2>&1
```

If no HAE payload arrives for 36 h, the alert text is one line and says to open Health Auto Export or charge/unlock the phone.
