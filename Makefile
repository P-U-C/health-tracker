.PHONY: ingest export test phase1 api staleness widget clean-generated

PY := RUST_LOG=error uv run --quiet python

ingest:
	$(PY) -m ingest.package_csvs --db data/health.duckdb

export:
	$(PY) -m export.csv_contracts --db data/health.duckdb --out data/exports

test:
	RUST_LOG=error uv run --quiet pytest -q

phase1: ingest export test

api:
	HEALTH_DB=data/health.duckdb RUST_LOG=error uv run --quiet uvicorn api.app:app --host 127.0.0.1 --port 8026

staleness:
	$(PY) -m jobs.staleness_monitor --db data/health.duckdb

widget:
	$(PY) -m jobs.widget_snapshot --db data/health.duckdb --out ~/.local/state/health-tracker-widget.json

clean-generated:
	rm -f data/health.duckdb
	rm -rf data/exports data/parquet .pytest_cache
