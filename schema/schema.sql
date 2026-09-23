-- Health system schema. DuckDB dialect; also valid SQLite/Postgres with trivial type changes.
-- Conventions: all timestamps stored in America/Vancouver local time (DST-aware conversion at ingest);
-- all masses kg; percentages as percent (17.2), never fractions; one row per (stream, timestamp, source).

-- ---------- Tier 2: Apple Health streams (mirror the 11 CSV contracts) ----------
CREATE TABLE IF NOT EXISTS resting_hr        (import_id TEXT PRIMARY KEY, date DATE, resting_hr INTEGER);
CREATE TABLE IF NOT EXISTS vo2max            (import_id TEXT PRIMARY KEY, date DATE, vo2max DOUBLE);
CREATE TABLE IF NOT EXISTS hrv_samples       (import_id TEXT PRIMARY KEY, ts TIMESTAMP, hrv_ms DOUBLE, source TEXT DEFAULT 'apple_watch');
CREATE TABLE IF NOT EXISTS spo2_samples      (import_id TEXT PRIMARY KEY, ts TIMESTAMP, spo2_pct DOUBLE);
CREATE TABLE IF NOT EXISTS hr_hourly         (import_id TEXT PRIMARY KEY, hour TIMESTAMP, hr_avg INTEGER, hr_min INTEGER, hr_max INTEGER, samples INTEGER);
CREATE TABLE IF NOT EXISTS activity_rings    (import_id TEXT PRIMARY KEY, date DATE, active_cal INTEGER, active_goal INTEGER, exercise_min INTEGER, exercise_goal INTEGER, stand_hrs INTEGER, stand_goal INTEGER);
CREATE TABLE IF NOT EXISTS daily_metrics (
  import_id TEXT PRIMARY KEY, date DATE, active_cal DOUBLE, basal_cal DOUBLE, steps DOUBLE, distance_km DOUBLE, flights DOUBLE,
  exercise_min DOUBLE, stand_min DOUBLE, asymmetry_pct DOUBLE, double_support_pct DOUBLE,
  walk_speed_kmh DOUBLE, walk_stride_cm DOUBLE,           -- converted from mi/h and inches at ingest
  stair_up_speed DOUBLE, stair_down_speed DOUBLE,
  run_speed_kmh DOUBLE, run_power_w DOUBLE, run_gct_ms DOUBLE, run_stride_cm DOUBLE, run_vert_osc_cm DOUBLE,
  resp_rate DOUBLE, physical_effort DOUBLE, daylight_min DOUBLE, env_audio_db DOUBLE, headphone_db DOUBLE);
CREATE TABLE IF NOT EXISTS workouts (
  import_id TEXT PRIMARY KEY, workout_id TEXT UNIQUE, start_ts TIMESTAMP, type TEXT, duration_min DOUBLE, distance_km DOUBLE, calories INTEGER,
  hr_avg INTEGER, hr_min INTEGER, hr_max INTEGER, source TEXT,
  trimp DOUBLE, srpe_load DOUBLE, session_rpe DOUBLE);         -- computed / logged
CREATE TABLE IF NOT EXISTS body_comp_samples (import_id TEXT PRIMARY KEY, date DATE, type TEXT, value DOUBLE, source TEXT);
CREATE TABLE IF NOT EXISTS sleep_segments   (import_id TEXT PRIMARY KEY, start_ts TIMESTAMP, end_ts TIMESTAMP, value TEXT, source TEXT);
CREATE TABLE IF NOT EXISTS nutrition_daily  (
  import_id TEXT PRIMARY KEY, date DATE, calcium_mg DOUBLE, calories DOUBLE, carbs_g DOUBLE, cholesterol_mg DOUBLE,
  fat_g DOUBLE, fiber_g DOUBLE, iron_mg DOUBLE, mono_fat_g DOUBLE, poly_fat_g DOUBLE, potassium_mg DOUBLE,
  protein_g DOUBLE, sat_fat_g DOUBLE, sodium_mg DOUBLE, sugar_g DOUBLE, vitamin_c_mg DOUBLE, notes TEXT);
CREATE TABLE IF NOT EXISTS nutrition_logs (
  meal_id TEXT PRIMARY KEY, occurred_at TIMESTAMP, local_date DATE, source TEXT, input_method TEXT,
  description TEXT, photo_ref TEXT,
  calories DOUBLE, protein_g DOUBLE, carbs_g DOUBLE, fat_g DOUBLE, fiber_g DOUBLE, sugar_g DOUBLE, sodium_mg DOUBLE,
  confidence TEXT, needs_review BOOLEAN, llm_status TEXT, llm_model TEXT, raw_json TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS readings (ts TIMESTAMP, source TEXT, metric TEXT, value DOUBLE, unit TEXT, notes TEXT, PRIMARY KEY (ts, source, metric)); -- manual / chest strap / BP cuff

-- ---------- Tier 1: ground truth ----------
CREATE TABLE IF NOT EXISTS dexa_scans (
  scan_number INTEGER, scan_date DATE PRIMARY KEY, scan_id TEXT, provider TEXT,
  weight_kg DOUBLE, fat_mass_kg DOUBLE, lean_bmc_kg DOUBLE, body_fat_pct DOUBLE, bf_yn_pctile INTEGER, bf_am_pctile INTEGER,
  almi_kg_m2 DOUBLE, almi_yn_pctile INTEGER, almi_am_pctile INTEGER,
  lmi_kg_m2 DOUBLE, lmi_yn_pctile INTEGER, lmi_am_pctile INTEGER,
  fmi_kg_m2 DOUBLE, fmi_yn_pctile INTEGER, fmi_am_pctile INTEGER,
  vat_mass_g DOUBLE, vat_volume_cm3 DOUBLE, vat_area_cm2 DOUBLE, appendicular_lean_bmc_kg DOUBLE,
  subtotal_fat_kg DOUBLE, subtotal_lean_bmc_kg DOUBLE, subtotal_pct_fat DOUBLE,
  trunk_fat_kg DOUBLE, trunk_pct_fat DOUBLE, android_pct_fat DOUBLE, gynoid_pct_fat DOUBLE, android_gynoid_ratio DOUBLE,
  pct_fat_trunk_legs_ratio DOUBLE, trunk_limb_fat_mass_ratio DOUBLE,
  l_arm_lean_bmc_kg DOUBLE, r_arm_lean_bmc_kg DOUBLE, l_leg_lean_bmc_kg DOUBLE, r_leg_lean_bmc_kg DOUBLE,
  leg_lean_asymmetry_pct DOUBLE, bmd_total_g_cm2 DOUBLE, bmd_t_score DOUBLE, bmd_z_score DOUBLE,
  reported_by TEXT, source_file TEXT,
  conditions_json TEXT);                                        -- fasted, time, days since training/fast
CREATE TABLE IF NOT EXISTS dexa_regional (import_id TEXT UNIQUE, scan_date DATE, region TEXT, fat_kg DOUBLE, lean_bmc_kg DOUBLE, total_kg DOUBLE, pct_fat DOUBLE, yn_pctile INTEGER, am_pctile INTEGER, PRIMARY KEY (scan_date, region));
CREATE TABLE IF NOT EXISTS labs (
  draw_id TEXT, draw_date DATE, lab TEXT, analyte_code TEXT, analyte_name TEXT, value DOUBLE, unit TEXT,
  ref_low DOUBLE, ref_high DOUBLE, target_low DOUBLE, target_high DOUBLE,
  fasting_hours DOUBLE, hours_since_training DOUBLE, days_since_fast INTEGER, phase_id TEXT, notes TEXT,
  PRIMARY KEY (draw_id, analyte_code));
CREATE TABLE IF NOT EXISTS lab_variation (analyte_code TEXT PRIMARY KEY, cv_analytical DOUBLE, cv_within_subject DOUBLE, rcv_pct DOUBLE, source TEXT);

-- ---------- Tier 0: genome (derived tables only; raw VCF stays encrypted outside the DB) ----------
CREATE TABLE IF NOT EXISTS genomics_variants (rsid TEXT PRIMARY KEY, gene TEXT, genotype TEXT, domain TEXT, evidence_grade TEXT, interpretation TEXT, source TEXT);
CREATE TABLE IF NOT EXISTS genomics_prs      (trait TEXT PRIMARY KEY, pgs_id TEXT, score DOUBLE, percentile DOUBLE, reference_population TEXT, computed_at DATE);
CREATE TABLE IF NOT EXISTS genomics_priors   (prior_id TEXT PRIMARY KEY, domain TEXT, gene TEXT, rsid TEXT, genotype TEXT, effect TEXT, evidence_grade TEXT,
  applies_to TEXT, adjustment_json TEXT, status TEXT DEFAULT 'dormant', tested_by TEXT, updated_at DATE);

-- ---------- Protocol state ----------
CREATE TABLE IF NOT EXISTS phases (
  phase_id TEXT PRIMARY KEY, name TEXT, kind TEXT,               -- deficit | maintenance | accrual | deload | fast | recovery
  start_date DATE, planned_end DATE, actual_end DATE, status TEXT, -- planned | active | exited | aborted
  entry_criteria_json TEXT, exit_criteria_json TEXT, rules_json TEXT, verdict TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS bands (band_id TEXT PRIMARY KEY, metric TEXT, low DOUBLE, high DOUBLE, unit TEXT, lsc DOUBLE, effective_from DATE, effective_to DATE, rationale TEXT);
CREATE TABLE IF NOT EXISTS tripwires (tripwire_id TEXT PRIMARY KEY, name TEXT, metric TEXT, "window" TEXT, rule_json TEXT, action TEXT, active BOOLEAN DEFAULT TRUE, phase_id TEXT);
CREATE TABLE IF NOT EXISTS tagouts (tagout_id TEXT PRIMARY KEY, start_ts TIMESTAMP, end_ts TIMESTAMP, streams TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS overrides (override_id TEXT PRIMARY KEY, ts TIMESTAMP, recommendation TEXT, decision TEXT, reason TEXT, outcome TEXT, phase_id TEXT);
CREATE TABLE IF NOT EXISTS events (event_id TEXT PRIMARY KEY, kind TEXT, start_ts TIMESTAMP, end_ts TIMESTAMP, streams_tagged_out TEXT, hypothesis TEXT, prediction TEXT, outcome TEXT, notes TEXT);
CREATE TABLE IF NOT EXISTS experiments (experiment_id TEXT PRIMARY KEY, name TEXT, prior_id TEXT, hypothesis TEXT, metric TEXT, predicted_effect TEXT, washout_days INTEGER,
  start_date DATE, end_date DATE, status TEXT, result_json TEXT, verdict TEXT);
CREATE TABLE IF NOT EXISTS strength_sets (session_date DATE, session_type TEXT, exercise TEXT, set_no INTEGER, load_kg DOUBLE, reps INTEGER, rpe DOUBLE, e1rm DOUBLE, notes TEXT, PRIMARY KEY (session_date, exercise, set_no));

-- ---------- Derived (rebuilt nightly, never hand-edited) ----------
CREATE TABLE IF NOT EXISTS derived_daily (
  date DATE PRIMARY KEY, phase_id TEXT, tagged_out BOOLEAN,
  weight_kg DOUBLE, weight_7d DOUBLE, weight_slope_14d DOUBLE, bf_pct DOUBLE, bf_7d DOUBLE, bf_dexa_calibrated DOUBLE, energy_balance_est DOUBLE,
  hrv_daily DOUBLE, hrv_night DOUBLE, hrv_7d DOUBLE, hrv_28d DOUBLE, hrv_swc DOUBLE, hrv_state TEXT, hrv_cv_7d DOUBLE,
  rhr DOUBLE, rhr_28d DOUBLE, rhr_swc DOUBLE, rhr_state TEXT, readiness_state TEXT,
  sleep_min DOUBLE, deep_min DOUBLE, rem_min DOUBLE, sleep_efficiency DOUBLE, sleep_midpoint DOUBLE, sleep_regularity_7d DOUBLE, sleep_debt_14d DOUBLE,
  resp_rate DOUBLE, resp_28d DOUBLE, spo2_mean DOUBLE, spo2_p5 DOUBLE, illness_flag BOOLEAN,
  load_day DOUBLE, acute_7d DOUBLE, chronic_28d DOUBLE, acwr DOUBLE, monotony_7d DOUBLE, strain_7d DOUBLE,
  aerobic_efficiency DOUBLE, vo2max_est DOUBLE, vo2max_volume_adj DOUBLE,
  tripwires_fired TEXT);
CREATE TABLE IF NOT EXISTS band_status (scan_date DATE, band_id TEXT, value DOUBLE, margin DOUBLE, margin_lsc DOUBLE, trend_3scan DOUBLE, status TEXT, PRIMARY KEY (scan_date, band_id));
CREATE TABLE IF NOT EXISTS calibrations (calib_id TEXT PRIMARY KEY, kind TEXT, computed_at DATE, params_json TEXT, n INTEGER, residual_sd DOUBLE); -- eufy→dexa, watch kcal→dexa EB, vo2max→volume
CREATE TABLE IF NOT EXISTS ingest_log (received_at TIMESTAMP, source TEXT, payload_hash TEXT, rows_upserted INTEGER, min_ts TIMESTAMP, max_ts TIMESTAMP, PRIMARY KEY (received_at, source));
CREATE TABLE IF NOT EXISTS apple_xml_backfills (run_id TEXT PRIMARY KEY, source_file TEXT, started_at TIMESTAMP, finished_at TIMESTAMP, report_json TEXT);
