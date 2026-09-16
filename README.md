# health-tracker

Private P-U-C repository for the personal health and exercise tracking system. It owns the data contracts, ingestion components, deterministic health state model, API, and dashboard/widget outputs.

The original package contents are still present: data, knowledge, schema, build brief, and analysis programme. The implementation now lives around those contracts.

```
README.md                      this file
PROMPT.md                      build brief for any coding agent (Claude Code, Codex, Cursor, OpenClaw…) — start here
PLAN.md                        prospective analysis programme: what runs, when, and what it decides
playbook/
  00_principles.md             measurement hierarchy, phase discipline, constraint identification, composability, privacy
  01_protocol_state.md         bands, tripwires, tag-outs, current phase, cadence, overrides, open items (seed for the state tables)
  02_data_dictionary.md        every file's schema, defects, unit caveats, aggregation rules (the ingest contract)
  03_analysis_methods.md       implementable formulas/windows/thresholds for every derived metric
  04_training_nutrition.md     the program, nutrition rules, supplements, DEXA history table
  05_genomics_and_labs.md      how DNA and semi-annual blood panels plug in: panels, targets, RCV, curated variant panel, priors model
  06_agent_system_prompt.md    runtime system prompt for whichever model narrates over the API (model-agnostic)
schema/schema.sql              DuckDB/SQLite-compatible schema: raw streams, ground truth, genome, protocol state, derived
data/
  manifest.json                row counts, date ranges, checksums, coverage warning
  apple_health/*.csv           11 CSVs from the Jan 2026 Apple Health export (see warning)
  dexa/dexa_scans.csv          9 DEXA scans, 2025-05-27 → 2026-08-31, converted to kg, with indices and percentiles
  dexa/dexa_regional.csv       regional breakdown, long format
  dexa/raw/*.txt               verbatim report text — CONTAINS PII, keep private
  templates/*.csv              labs, strength log, events, manual readings — the four capture streams that did not exist before
reference/training_program_posture_density.md   the actual A/B lifting program (seed for the strength log)
```

## Product Shape

- Integrations are components: Health Auto Export, Apple Health XML, BodyStats/DEXA, labs, genome, push, API, dashboard, and life-dashboard widget.
- Private runtime data stays local: `.env`, DuckDB, imports, exports, raw DEXA reports, BodyStats sessions, and generated snapshots are ignored.
- Public exposure is intentionally narrow: only `/status` and authenticated `/ingest/hae` are behind the Cloudflare tunnel today.
- The future primary surface is a polished private dashboard for health/exercise statistics. The life dashboard receives a small static JSON snapshot, not the whole DB.

See:

- `docs/product_architecture.md`
- `docs/life_dashboard_widget.md`
- `config/components.yaml`

## Order of operations on the new machine
1. Unpack into an empty private repo. Commit as-is (`data/dexa/raw/` should be git-crypt/age-encrypted or gitignored before any remote push).
2. Hand `PROMPT.md` to the coding agent. It will read the playbook and schema, then build in six phases with exit criteria.
3. Export a fresh Apple Health archive from the iPhone (Health app → profile → Export All Health Data) and run the bulk backfill (PROMPT §5.2) — the package CSVs end 2026-01-30.
4. Install Health Auto Export on the phone, create a REST automation to the ingest endpoint (PROMPT §5.1).
5. Answer the six open items in `playbook/01_protocol_state.md` so the state tables start true.
6. Start the strength log on the first session after the pipe is live.
7. Book the December DEXA and a blood draw 1–2 weeks after it; when the genome is sequenced, run `ingest/genome/`.

## Warnings
- **Coverage gap**: Apple Health CSVs end 2026-01-29/30. Six DEXA scans have no wearable context until the backfill runs.
- **Known defects in the CSVs** (fixed at ingest, see `playbook/02`): summer timestamps one hour early; `body_fat_pct` stored as a fraction; `run_speed_kmh`/`walk_speed_kmh` are mi/h; `walk_stride_cm` is inches; `nutrition_daily` dead since 2023.
- **PII**: `data/dexa/raw/` holds name, email and date of birth. Everything else in the package is de-identified apart from the subject's alias.
- **Not medical advice**: targets in `playbook/05` are optimisation targets used in preventive practice; lab reference intervals and clinicians decide anything clinical.
