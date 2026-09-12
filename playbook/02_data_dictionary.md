# 02 — Data dictionary

Every file in `data/`, its schema, provenance, known defects, and the aggregation rule that must be applied before the data is used. Treat this as the contract the ingest layer must reproduce.

## Coverage warning (read first)

All Apple Health CSVs end **2026-01-29/30**. Six DEXA scans (Feb–Aug 2026) therefore have no matching wearable data in this package. Before any 2026 analysis: run a fresh Apple Health export through the bulk backfill (see `PROMPT.md` §Ingest), or drop in the regenerated `health_data_2026-08/` set if it still exists on the subject's side. Merge rule that was used previously and must be kept: **keep old rows exactly, append only rows with dates strictly after each file's previous max** (the old export had hourly HR downsampled 43–68% in later re-exports — never overwrite history with a newer export).

Timezone defect in these files: Apple stamps every record with the offset in force at export time (this export: −0800 PST), so **summer (PDT) timestamps in these CSVs are one hour early**. Convert with `zoneinfo("America/Vancouver")` per record at ingest. Winter records are correct.

## `data/apple_health/`

| file | grain | rows | span | key columns | notes |
|---|---|---|---|---|---|
| `resting_hr.csv` | daily | 571 | 2023-06-19 → 2026-01-29 | `date, resting_hr` (bpm) | Apple's daily RHR estimate. Missing days = watch not worn overnight. |
| `hrv.csv` | sample (~8/day) | 4,946 | 2023-06-19 → 2026-01-29 | `date` (local datetime, minute precision), `hrv_ms` | **SDNN**, not rMSSD. Sampled opportunistically (sleep + still periods). **Group by calendar day → mean (or median) before any windowing.** Prefer the 00:00–07:00 subset for a consistent nightly value; keep both. |
| `vo2max.csv` | per estimate | 145 | 2023-06-25 → 2026-01-28 | `date, vo2max` (mL/kg/min) | Apple estimator; only updates on outdoor walk/run with GPS. Volume-confounded (see `03_analysis_methods`). |
| `oxygen_saturation.csv` | sample | 8,141 | 2023-06-19 → 2026-01-29 | `date` (datetime), `spo2_pct` | Mostly overnight samples. Aggregate nightly mean and 5th percentile. |
| `heart_rate_hourly.csv` | hourly | 15,207 | 2017-02-05 → 2026-01-29 | `datetime` (`YYYY-MM-DD HH`), `hr_avg, hr_min, hr_max, samples` | `samples` = raw HR readings in the hour. Later re-exports downsample this; preserve existing rows. |
| `activity_rings.csv` | daily | 743 | 2023-05-12 → 2026-01-29 | `active_cal, active_goal, exercise_min, exercise_goal, stand_hrs, stand_goal` | Watch ring summaries. Goals change over time. |
| `daily_metrics.csv` | daily | 1,722 | 2017-02-05 → 2026-01-30 | 23 metrics (see below) | Sparse before 2023. Column names lie for three metrics (imperial-locale export): **`run_speed_kmh` and `walk_speed_kmh` are mi/h; `walk_stride_cm` is inches.** Convert at ingest (×1.609344, ×2.54) and rename. |
| `workouts.csv` | per workout | 699 | 2017-02-07 → 2026-01-29 | `date` (start datetime), `type, duration_min, distance_km, calories, hr_avg, hr_min, hr_max, source` | Types: Running 204, Functional Strength 193, Walking 68, Cycling 57, Yoga 47, Swimming 35, Rowing 35, Strength Training 26, Kickboxing 17, others. `hr_* = 0` means no HR (pre-Watch / third-party). Sources: Apple Watch 514, Connect 88, Nike Run Club 58, Daily Yoga 36. Pre-Aug-2026 exports missed distance for swim/cycle/snow. |
| `body_composition.csv` | long (date,type,value,source) | 2,133 | 2017-01-08 → 2026-01-30 | types: `weight_kg, body_fat_pct, lean_mass_kg, bmi, height_cm` | **`body_fat_pct` is a fraction (0.172 = 17.2%).** Sources: `eufy Life` 1,808 (daily BIA scale, 2023→), MyFitnessPal 236, Connect 84, Health 4. Use `source == 'eufy Life'` for the scale series; `type == 'weight_kg'`. Eufy BF% reads ~0.8–1.0 pp above DEXA historically (+0.3 pp on 2026-07-09); recalibrate at every scan. |
| `sleep.csv` | segment | 23,917 | 2017-02-04 → 2026-01-25 | `start, end, value, source` | `value` ∈ InBed 12,985 · AsleepCore 4,521 · AsleepREM 1,732 · AsleepUnspecified 1,361 · AsleepDeep 1,106 · Awake 2,212. Sources: Apple Watch 11,588, iPhone 8,712, Clock 2,068, Connect 1,543. **Rules:** date a night by `start` shifted −6 h (so 01:00 belongs to the previous evening); sleep duration = sum of `Asleep*` segments only; stage split available only when source = Watch; when Watch and iPhone overlap the same night, keep Watch and drop the iPhone/Clock InBed rows. |
| `nutrition_daily.csv` | daily | 110 | 2017-02-07 → 2023-08-30 | macros + micros | **Dead since 2023.** Keep for schema only. Do not use for any current analysis. |

### `daily_metrics.csv` columns
`active_cal, basal_cal` (kcal) · `steps, distance_km, flights` · `exercise_min, stand_min` · `asymmetry_pct, double_support_pct, walk_speed_kmh(→mi/h!), walk_stride_cm(→in!), stair_up_speed, stair_down_speed` (gait; m/s for stairs) · `run_speed_kmh(→mi/h!), run_power_w, run_gct_ms, run_stride_cm, run_vert_osc_cm` (running form, sparse) · `resp_rate` (brpm, overnight) · `physical_effort` (MET-ish) · `daylight_min` · `env_audio_db, headphone_db`.

Completeness in the last 400 days: walk_speed/stride/double_support 100%, steps/distance 99%, asymmetry 97%, flights 98%, active_cal 54%, basal_cal 57%, resp_rate 33%, daylight 32%, running-form metrics 7%.

## `data/dexa/`

Provider: BodyStats, Vancouver — Hologic Horizon W (S/N 309700M), analysis software 13.6.x, NHANES reference population (YN = young normal percentile, AM = age-matched percentile). Reports are delivered as ZIP bundles renamed `.pdf` (`archive_see_email_first_*_A.pdf`), containing page JPEGs + page text; `1.txt` bone summary, `2.txt` regional composition + adipose indices, `3.txt` lean indices + impression, `4–5.txt` BMD detail/images. Original values are in **lb**; the CSVs here are converted to **kg** (×0.45359237).

### `dexa_scans.csv` — one row per scan (9 scans, 2025-05-27 → 2026-08-31)
`scan_number, scan_date, scan_id, weight_kg, fat_mass_kg, lean_bmc_kg, body_fat_pct, bf_yn_pctile, bf_am_pctile, almi_kg_m2 (+pctiles), lmi_kg_m2 (+pctiles), fmi_kg_m2 (+pctiles), vat_mass_g, vat_volume_cm3, vat_area_cm2, appendicular_lean_bmc_kg, subtotal_* (excludes head), trunk_fat_kg, trunk_pct_fat, android_pct_fat, gynoid_pct_fat, android_gynoid_ratio, pct_fat_trunk_legs_ratio, trunk_limb_fat_mass_ratio, l/r_arm_lean_bmc_kg, l/r_leg_lean_bmc_kg, leg_lean_asymmetry_pct ((R−L)/L), bmd_total_g_cm2, bmd_t_score, bmd_z_score, provider, reported_by, source_file`

`weight_kg` here is DEXA total mass (fat + lean + BMC incl. head), which runs ~0.5–1 kg under morning scale weight on the same day (no clothes/food differences aside). "Lean + BMC" is the band metric, not lean alone.

### `dexa_regional.csv` — long format (90 rows)
`scan_date, region ∈ {L Arm, R Arm, Trunk, L Leg, R Leg, Subtotal, Head, Total, Android, Gynoid}, fat_kg, lean_bmc_kg, total_kg, pct_fat, yn_pctile, am_pctile`

### `raw/dexa_<date>_report.txt`
Verbatim page text for traceability. **Contains PII (name, email, date of birth).** Keep the repository private; do not send these files to any hosted model.

Subject constants from the reports: male, born 1984-10 (41 at package date), height 172–173 cm (68.0 in on the DEXA, 172.0 cm on the scale).

## Not included, but referenced
- `parse_export.py` (Apple Health `export.xml` streaming parser, Aug 2026) — lives on the subject's side; its behaviour is specified in `PROMPT.md` so it can be rewritten.
- Strength training log — **never existed**. Schema provided in `schema/schema.sql`; exercise list seeded from `reference/training_program_posture_density.md`.
- Post-fast blood panel (recommended 2026-09-05: CK, Na/K/Mg/phosphate, creatinine/eGFR, CBC) — status unknown; if drawn, it is the first row set in `labs`.
