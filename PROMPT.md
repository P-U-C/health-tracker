# BUILD BRIEF — personal health system ("the pipe, the state model, the analyst")

You are a coding agent working on a fresh machine with this package unpacked at the repo root. Read, in order: `README.md`, `playbook/00_principles.md`, `playbook/02_data_dictionary.md`, `schema/schema.sql`, `PLAN.md`. Then build. Ask at most five questions before starting; make reasonable assumptions and log them in `DECISIONS.md`.

## 1. What this is for
One subject (41 M, Vancouver, technical, terse) runs a quantified body-composition and fitness program anchored on quarterly DEXA scans and semi-annual blood panels, tracked daily by Apple Watch and a Eufy scale, with a genome sequence coming. Today the data pipeline is a manual Apple Health XML export re-parsed every few months, the protocol state lives in chat transcripts, and the interpretation know-how lives inside one vendor's chat product. Build a system that is:

1. **Always fresh** — Apple Health data arrives automatically with < 24 h lag, no manual steps.
2. **Stateful** — phases, bands, tripwires, tag-outs, overrides and experiments are tables, and every day is inside a labeled phase.
3. **Deterministic first** — ingest, derived metrics, rules and alerts are code. No LLM in the daily loop.
4. **Composable** — one OpenAPI service; MCP, CLI and chat are adapters over it. Any model, any client, swappable in an afternoon. Data in files the subject owns.
5. **Tiered** — genome sets priors, DEXA/labs are ground truth, wearables are calibrated proxies (see `playbook/00_principles.md`). This tiering, with explicit noise floors and calibration at every anchor, is the product. Do not build a generic dashboard.

## 2. Non-negotiables
- No proprietary readiness/recovery composites. Every derived metric is defined in `playbook/03_analysis_methods.md` with its window and threshold; implement exactly those, parameterised in `config/`.
- Every reported number carries a unit and, where defined, its noise floor (LSC/SWC/RCV).
- Time windows anchor to the dataset max date, not the system clock.
- Timestamps converted to `America/Vancouver` DST-aware per record. Never overwrite historical rows with a newer export (append-only by date; upsert by key).
- Raw genome (VCF/CRAM) and raw DEXA report text never enter the DB or any model context. Derived tables only.
- Overrides are logged, never argued. The service exposes `log_override` and the analyst prompt (`playbook/06`) forbids moralising.
- Keep the 11 Apple Health CSV contracts (`playbook/02`) as the export format so existing analyses keep working: `make export` regenerates them from the DB at any time.

## 3. Stack (defaults; change with a note in `DECISIONS.md`)
- Python 3.12, FastAPI, DuckDB (single file `data/health.duckdb`; Parquet snapshots in `data/parquet/`). Postgres is over-engineering at n = 1.
- `fastmcp` to generate the MCP server from the OpenAPI spec; `typer` CLI; `apscheduler` or systemd timers for the nightly job.
- Deployment target: a Proxmox LXC/VM on the subject's homelab; public HTTPS via Cloudflare Tunnel (remote MCP clients connect from the vendor's cloud, so the endpoint must be publicly reachable). Auth: OAuth on the MCP server (FastMCP auth providers) — MCP client UIs generally do not support custom headers; bearer token for the REST ingest endpoint.
- Push: `ntfy` (self-hosted) and/or Telegram bot; the subject already runs OpenClaw on the homelab and can front it with any model provider.
- Tests: pytest; fixtures from `data/` samples.

## 4. Repo layout
```
health/
  config/            thresholds.yaml (windows, SWC factor, LSC defaults, bands seed), units.yaml
  ingest/            hae_rest.py (Health Auto Export JSON), apple_export_xml.py (bulk backfill), dexa_bundle.py, labs_csv.py, genome/ (bcftools + panel)
  core/              schema.sql loader, derived.py (03 methods), rules.py (tripwires, tag-outs, illness detector), calibrate.py, constraint.py
  api/               FastAPI app + OpenAPI; adapters/mcp.py; adapters/cli.py
  jobs/              nightly.py, weekly.py, per_scan.py, per_draw.py, staleness_monitor.py, push.py
  playbook/          (copied from package; canonical knowledge, loaded by the analyst)
  data/              health.duckdb, parquet/, imports/, exports/
  tests/
  DECISIONS.md
```

## 5. Ingest
### 5.1 Live: Health Auto Export → REST
The iOS app Health Auto Export (Premium, automations) POSTs JSON to `POST /ingest/hae` on a schedule (hourly when the phone is unlocked; iOS decides actual timing). Payload shape: `{"data": {"metrics": [{"name": "heart_rate", "units": "bpm", "data": [{"date": "...", "qty": ..., "Avg": ..., "Min": ..., "Max": ...}]}], "workouts": [...]}}`. Requirements:
- Idempotent upsert on (stream, timestamp[, source]); return counts; write `ingest_log`.
- Map HAE metric names to the schema (`heart_rate` → `hr_hourly` via hourly aggregation when aggregation is set to hour; `heart_rate_variability` → `hrv_samples`; `resting_heart_rate`; `vo2_max`; `blood_oxygen_saturation`; `sleep_analysis` (stages) → `sleep_segments`; `weight_body_mass`, `body_fat_percentage` (convert fraction→percent if < 1), `lean_body_mass` → `body_comp_samples` with source; `step_count`, `walking_speed`, `walking_step_length`, `walking_double_support_percentage`, `walking_asymmetry_percentage`, `stair_speed_up/down`, `respiratory_rate`, `time_in_daylight`, `active_energy`, `basal_energy_burned`, `apple_exercise_time`, `apple_stand_time`, `flights_climbed`, `physical_effort`, running form metrics, `environmental_audio_exposure`, `headphone_audio_exposure` → `daily_metrics`; workouts → `workouts` with per-workout HR summary and distance for swim/cycle/snow).
- Units: HAE sends units per metric; normalise to the schema units (km, kg, cm, km/h, %). Do not trust column names from the old CSVs.
- `jobs/staleness_monitor.py`: if no payload for a stream in 36 h → push a one-line alert (HAE cannot run while the phone is locked; the fix is opening the app or charging the phone, not code).

### 5.2 Bulk backfill: Apple Health `export.xml`
Reimplement the previous parser: streaming `iterparse` over a 1–3 GB XML, per-record DST-aware conversion to Vancouver local time (Apple stamps the export-time offset on every record), body-fat fraction → percent, height already cm, hourly HR aggregation with sample counts, sleep segments with source, workouts with `WorkoutStatistics` for HR and distance. Merge rule: keep existing rows, append only rows after each stream's max timestamp; report per-stream counts before/after. Run it once on a fresh export to close the Jan-30-2026 → today gap, then keep it as the disaster-recovery path.

### 5.3 DEXA bundles
BodyStats delivers a ZIP renamed `.pdf` with page images + page text (`1.txt` bone, `2.txt` regional + adipose indices, `3.txt` lean indices). Port `data/dexa/` parsing (the regexes are simple; see the raw text under `data/dexa/raw/`). Watch a `data/imports/dexa/` folder (or an IMAP mailbox) and ingest on arrival. Values arrive in lb → store kg.

### 5.4 Labs and genome
Labs: `data/templates/labs_template.csv` → `labs`; `lab_variation` seeded from the EFLM biological-variation database for the analytes in `playbook/05`. Genome: `ingest/genome/` runs `bcftools norm` + panel extraction + `pgsc_calc`, writes only `genomics_variants`, `genomics_prs`, `genomics_priors`. Raw files stay in an encrypted directory outside `data/`.

## 6. Core
- `core/derived.py` computes `derived_daily` exactly per `playbook/03` (A3, A4, B1–B4, C1–C2, C5, D), with tag-outs applied to baselines.
- `core/rules.py` evaluates tripwires (seed from `playbook/01`), the illness detector, band status per scan, phase-exit criteria; emits `alerts` (table + push). Silent when nothing fires.
- `core/calibrate.py`: Eufy→DEXA regression, Watch-kcal→DEXA energy-balance factor, VO2max volume adjustment; rows in `calibrations`.
- `core/constraint.py`: quarterly constraint scan (`playbook/03 §F`).
- `jobs/per_scan.py`: on a new DEXA row → A1–A7, band verdict, phase-decision proposal with pre-committed exit criteria, markdown report to `data/exports/reports/`.
- `jobs/per_draw.py`: on a new lab draw → RCV deltas, target distances, cross-link tests, prior status updates, markdown report.

## 7. API (OpenAPI) — minimum surface
`GET /status` (phase, days remaining, band summary, weight 7d vs tripwire, HRV/RHR state, sleep, load, open experiments, next anchors, data freshness) · `GET /metrics/{name}?window=&agg=` · `GET /bands/status` · `GET /dexa/compare?a=&b=` · `GET /phases/current` · `POST /phases/propose` · `POST /log/set` · `POST /log/event` · `POST /log/override` · `POST /log/reading` · `GET /labs/latest` · `GET /labs/delta` · `GET /priors/active` · `GET /experiments/open` · `GET /constraint/scan` · `POST /ingest/hae` · `POST /ingest/dexa` · `POST /ingest/labs` · `GET /export/csv`.
Generate the MCP server from this spec (tool names = operationIds in `playbook/06`), and a CLI with the same verbs. Everything the chat can do, the CLI can do.

## 8. Capture (LLM-free paths must exist)
- iOS Shortcut: dictation → POST `/log/set` / `/log/event` / `/log/reading` (bearer). Provide the Shortcut recipe in `docs/capture.md`.
- Chat path: the analyst (any model, `playbook/06`) parses freeform and calls the same endpoints.

## 9. Push
`jobs/push.py`: daily one-message status (deterministic template, ≤ 8 lines, silent unless a rule fired or an anchor is within 7 days); weekly review; per-scan and per-draw reports as markdown links. Channels: ntfy + Telegram via config.

## 10. Delivery phases (each with an exit criterion — stop and report at each exit)
1. **Data foundation**: schema loaded; package CSVs + DEXA ingested; `make export` reproduces the 11 CSVs byte-equivalent (post timezone/unit normalisation documented); tests green. *Exit: row counts match `data/manifest.json`; `dexa_scans` has 9 rows.*
2. **Pipe**: `/ingest/hae` live behind the tunnel; bulk backfill run on a fresh export; staleness monitor on. *Exit: 14 consecutive days with < 24 h lag and zero manual steps.*
3. **Derived + rules + push**: nightly job produces `derived_daily`; tripwires seeded; daily push working. *Exit: a tripwire fires on its own from live data.*
4. **Adapters**: OpenAPI complete; MCP server generated and connected to at least two different clients (e.g. OpenClaw + one vendor chat); CLI. *Exit: a scale reading typed into any client is answered with band context from live data.*
5. **Anchors**: per-scan and per-draw jobs; labs template import; calibration jobs. *Exit: the December 2026 DEXA produces the scan report automatically.*
6. **Genome**: pipeline + priors table + experiment generator. *Exit: `priors_active` returns graded priors and one caffeine-timing experiment is queued if CYP1A2 warrants it.*

## 11. Working with the subject
Terse, data-referenced. Log assumptions and overrides in `DECISIONS.md`. Do not pad reports. When a rule in the playbook conflicts with observed data, report the conflict; do not silently change the rule.
