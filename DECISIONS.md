# DECISIONS

## 2026-09-12 Phase 1

- No questions asked before build; package files are sufficient for Phase 1.
- Host has Python 3.10.12 and no `python3.12`; Phase 1 targets `>=3.10` and keeps code 3.12-compatible.
- DuckDB was not installed in the system Python; dependency is declared in `pyproject.toml` and run through `uv`.
- `schema/schema.sql` conflicted with `playbook/02_data_dictionary.md` and `data/manifest.json`: several Apple CSVs have duplicate logical keys and `nutrition_daily`/`dexa_scans` contain columns omitted from the seed schema. For Phase 1, manifest/data-dictionary row preservation wins. Tables keep numeric/date types but add hidden `import_id` columns where needed and include all manifest columns required for export.
- `make export` emits normalized contract CSVs under `data/exports/`: body-fat fractions become percent, imperial-locale gait speeds/stride become metric, and timestamp streams in Vancouver DST are shifted +1 h to repair the package export-time-offset defect. Byte equivalence is tested against this documented normalized form, not against the defective source bytes.

## 2026-09-12 Phase 2

- No additional questions asked. Fresh Apple Health `export.xml`, Cloudflare account/tunnel ID, and production ingest bearer token were not present on disk, so Phase 2 is implemented and locally testable but the 14-day live exit clock cannot start from this turn.
- `POST /ingest/hae` requires `Authorization: Bearer $HEALTH_INGEST_TOKEN`. If the token is unset, the endpoint returns 503 unless `HEALTH_ALLOW_DEV_AUTH=1` is set for local development.
- Public tunnel setup is documented, not provisioned. A stable Cloudflare Tunnel should terminate to `127.0.0.1:8026`; no quick tunnel was started because the HAE phone automation needs a stable URL.
- Staleness alerts use HAE ingest-log receive time, not derived metric windows. The fix text is operational: open Health Auto Export or charge/unlock the phone.

## 2026-09-13 Phase 2 Export Intake

- Telegram text updates `493821966` and `493821968` reached the Codex session with `images=[]`, `local_images=[]`, `audio=[]`, `local_audio=[]`, and `text_elements=[]`. Processed update `493821967` is present in the local completed-update ledger but absent from the Codex session, consistent with an unsupported document attachment.
- Filesystem scans found `0` Apple Health export files or ZIPs created by that Telegram message. A single non-polling Telegram `getUpdates` check for offsets `493821960+` returned `0` updates, so the raw file id is no longer recoverable from the bot API.

## 2026-09-16 BodyStats Dashboard Pull

- BodyStats magic link was expired, so the email-code flow was used with the existing DEXA report patient email. No auth code or session cookie is stored in git; all fetched artifacts live under ignored `data/imports/dexa/bodystats_2026-09-16/`.
- Pulled `results-data`, `original-reports`, `tests`, `profile`, 4 original DEXA PDFs, and available scan PNGs. BodyStats returned 13 dashboard scan rows: the 9 canonical protocol scans plus extra/duplicate early scans on 2025-05-27/28/30 and 2025-06-27.
- Canonical `dexa_scans` was left unchanged because it is keyed one row per `scan_date`, and the playbook's current phase history names 9 scans. The BodyStats data is staged for a future duplicate-safe DEXA source table or an explicit policy for precision/duplicate early scans.
