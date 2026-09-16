# Phase 1 Normalization

`make export` regenerates the package CSV contracts from `data/health.duckdb` after the Phase 1 ingest normalizations required by `playbook/02_data_dictionary.md`.

Applied normalizations:

- Timestamp streams (`hrv`, `oxygen_saturation`, `heart_rate_hourly`, `sleep`, `workouts`) are treated as `America/Vancouver` local clock readings. Rows whose local timestamp falls inside Vancouver daylight-saving time are shifted +1 hour because the package CSVs were stamped with the export-time PST offset.
- `body_composition.value` is multiplied by 100 when `type == body_fat_pct` and the stored value is `< 1`.
- `daily_metrics.walk_speed_kmh` and `daily_metrics.run_speed_kmh` are converted from mi/h to km/h with factor `1.609344`.
- `daily_metrics.walk_stride_cm` is converted from inches to cm with factor `2.54`.
- Generated helper fields such as `import_id`, `workout_id`, `source` defaults, and future derived fields are not exported.
