from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent

from fastapi.testclient import TestClient

from api.app import app
from core.schema import connect, load_schema, table_count
from ingest.apple_export_xml import backfill_xml
from ingest.hae_rest import ingest_hae_payload
from core.dashboard import build_dashboard_model
from jobs.staleness_monitor import check_staleness
from jobs.widget_snapshot import build_snapshot


def sample_hae_payload() -> dict:
    return {
        "data": {
            "metrics": [
                {
                    "name": "heart_rate",
                    "units": "bpm",
                    "data": [
                        {"date": "2026-09-12T10:15:00-07:00", "Avg": 70, "Min": 62, "Max": 91, "samples": 4},
                        {"date": "2026-09-12T10:45:00-07:00", "qty": 74},
                    ],
                },
                {"name": "heart_rate_variability", "units": "ms", "data": [{"date": "2026-09-12T03:05:00-07:00", "qty": 51.2}]},
                {"name": "resting_heart_rate", "units": "bpm", "data": [{"date": "2026-09-12", "qty": 57}]},
                {"name": "vo2_max", "units": "mL/kg/min", "data": [{"date": "2026-09-12", "qty": 47.5}]},
                {"name": "blood_oxygen_saturation", "units": "%", "data": [{"date": "2026-09-12T02:00:00-07:00", "qty": 0.97}]},
                {
                    "name": "sleep_analysis",
                    "data": [
                        {
                            "start": "2026-09-11T23:30:00-07:00",
                            "end": "2026-09-12T06:45:00-07:00",
                            "value": "AsleepCore",
                            "source": "Apple Watch",
                        }
                    ],
                },
                {"name": "weight_body_mass", "units": "lb", "data": [{"date": "2026-09-12T07:00:00-07:00", "qty": 180, "source": "eufy Life"}]},
                {"name": "body_fat_percentage", "units": "%", "data": [{"date": "2026-09-12T07:00:00-07:00", "qty": 0.185, "source": "eufy Life"}]},
                {"name": "lean_body_mass", "units": "kg", "data": [{"date": "2026-09-12T07:00:00-07:00", "qty": 64.1, "source": "eufy Life"}]},
                {"name": "step_count", "units": "count", "data": [{"date": "2026-09-12", "qty": 9000}]},
                {"name": "walking_speed", "units": "mph", "data": [{"date": "2026-09-12", "qty": 3.0}]},
                {"name": "walking_step_length", "units": "in", "data": [{"date": "2026-09-12", "qty": 30}]},
                {"name": "active_energy", "units": "kcal", "data": [{"date": "2026-09-12", "qty": 700}]},
            ],
            "workouts": [
                {
                    "date": "2026-09-12T17:00:00-07:00",
                    "type": "Running",
                    "duration": 30,
                    "durationUnit": "min",
                    "distance": 5,
                    "distanceUnit": "km",
                    "calories": 400,
                    "hr_avg": 145,
                    "hr_min": 95,
                    "hr_max": 180,
                    "source": "Apple Watch",
                }
            ],
        }
    }


def test_hae_ingest_is_idempotent_and_normalizes_units(tmp_path: Path) -> None:
    db = tmp_path / "health.duckdb"
    first = ingest_hae_payload(sample_hae_payload(), db)
    second = ingest_hae_payload(sample_hae_payload(), db)

    assert first["inserted"] == 11
    assert second["inserted"] == 0
    assert second["updated"] == 11

    conn = connect(db)
    try:
        assert table_count(conn, "hr_hourly") == 1
        assert table_count(conn, "hrv_samples") == 1
        assert table_count(conn, "body_comp_samples") == 3
        assert table_count(conn, "daily_metrics") == 1
        row = conn.execute(
            """
            SELECT steps, walk_speed_kmh, walk_stride_cm, active_cal
            FROM daily_metrics
            WHERE date = DATE '2026-09-12'
            """
        ).fetchone()
        assert row == (9000.0, 4.828032, 76.2, 700.0)
        bf = conn.execute("SELECT value FROM body_comp_samples WHERE type = 'body_fat_pct'").fetchone()[0]
        assert bf == 18.5
    finally:
        conn.close()


def test_hae_ingest_dedupes_rows_with_same_import_id(tmp_path: Path) -> None:
    db = tmp_path / "health.duckdb"
    payload = {
        "data": {
            "metrics": [
                {
                    "name": "body_fat_percentage",
                    "units": "%",
                    "data": [
                        {"date": "2026-09-12T07:00:00-07:00", "qty": 0.181, "source": "eufy Life"},
                        {"date": "2026-09-12T07:01:00-07:00", "qty": 0.185, "source": "eufy Life"},
                    ],
                }
            ]
        }
    }

    result = ingest_hae_payload(payload, db)

    assert result["rows_seen"] == 2
    assert result["inserted"] == 1
    conn = connect(db)
    try:
        assert table_count(conn, "body_comp_samples") == 1
        value = conn.execute("SELECT value FROM body_comp_samples WHERE type = 'body_fat_pct'").fetchone()[0]
        assert value == 18.5
    finally:
        conn.close()


def test_api_requires_bearer_and_returns_counts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HEALTH_DB", str(tmp_path / "health.duckdb"))
    monkeypatch.setenv("HEALTH_INGEST_TOKEN", "test-token")
    client = TestClient(app)

    assert client.post("/ingest/hae", json=sample_hae_payload()).status_code == 401
    response = client.post("/ingest/hae", json=sample_hae_payload(), headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    body = response.json()
    assert body["rows_seen"] == 15
    assert body["inserted"] == 11


def test_staleness_monitor_accepts_recent_hae_payload(tmp_path: Path) -> None:
    db = tmp_path / "health.duckdb"
    ingest_hae_payload(sample_hae_payload(), db)
    result = check_staleness(db)
    assert result["ok"] is True
    assert result["stream_count"] >= 8
    assert result["stale_count"] == 0


def test_widget_snapshot_exposes_life_dashboard_contract(tmp_path: Path) -> None:
    db = tmp_path / "health.duckdb"
    ingest_hae_payload(sample_hae_payload(), db)

    snapshot = build_snapshot(db)

    assert snapshot["status"] == "ok"
    assert snapshot["summary"]["weight_kg"] == 81.65
    assert snapshot["summary"]["body_fat_pct"] == 18.5
    assert snapshot["summary"]["hae_stream_count"] >= 8
    assert snapshot["items"][0]["title"] == "live health pipe fresh"


def test_dashboard_model_keeps_dexa_eufy_and_estimate_separate(tmp_path: Path) -> None:
    db = tmp_path / "health.duckdb"
    ingest_hae_payload(sample_hae_payload(), db)
    conn = connect(db)
    try:
        load_schema(conn)
        conn.execute(
            """
            INSERT INTO dexa_scans (
              scan_number, scan_date, provider, weight_kg, fat_mass_kg, lean_bmc_kg,
              body_fat_pct, vat_mass_g, android_gynoid_ratio, bmd_total_g_cm2
            ) VALUES (1, DATE '2026-09-12', 'Test DEXA', 81.65, 13.88, 67.77, 17.0, 250, 1.05, 1.18)
            """
        )
    finally:
        conn.close()

    model = build_dashboard_model(db)

    assert model["hero"]["latest_dexa"]["body_fat_pct"] == 17.0
    assert model["hero"]["estimate"]["available"] is True
    assert model["hero"]["estimate"]["body_fat_pct_mid"] == 17.0
    assert model["source_policy"]["body_fat"] == ["DEXA measured", "Eufy measured", "Estimated from DEXA + Eufy trend"]
    body_labels = {metric["label"]: metric["source_label"] for metric in model["body"]["metrics"]}
    assert body_labels["DEXA body fat"] == "DEXA measured"
    assert body_labels["Estimated current body fat"] == "Estimated from DEXA + Eufy trend"


def test_dashboard_routes_render_private_overview(tmp_path: Path, monkeypatch) -> None:
    db = tmp_path / "health.duckdb"
    ingest_hae_payload(sample_hae_payload(), db)
    monkeypatch.setenv("HEALTH_DB", str(db))
    monkeypatch.setenv("HEALTH_DASHBOARD_USER", "chad")
    monkeypatch.setenv("HEALTH_DASHBOARD_PASSWORD", "test-password")

    client = TestClient(app)
    assert client.get("/dashboard").status_code == 401
    api_response = client.get("/api/dashboard/overview", auth=("chad", "test-password"))
    html_response = client.get("/dashboard", auth=("chad", "test-password"))

    assert api_response.status_code == 200
    assert api_response.json()["hero"]["smoothed_weight_kg"] == 81.65
    assert html_response.status_code == 200
    assert "Health Optimization Dashboard" in html_response.text
    assert "DEXA anchors, Eufy trend" in html_response.text
    assert "Add source" in html_response.text


def test_apple_xml_backfill_streams_and_appends_after_existing_max(tmp_path: Path) -> None:
    db = tmp_path / "health.duckdb"
    conn = connect(db)
    try:
        load_schema(conn)
    finally:
        conn.close()

    xml = tmp_path / "export.xml"
    xml.write_text(
        dedent(
            """\
            <?xml version="1.0" encoding="UTF-8"?>
            <HealthData>
              <Record type="HKQuantityTypeIdentifierRestingHeartRate" sourceName="Apple Watch" unit="count/min" startDate="2026-09-12 07:00:00 -0700" endDate="2026-09-12 07:00:00 -0700" value="57"/>
              <Record type="HKQuantityTypeIdentifierBodyFatPercentage" sourceName="eufy Life" unit="%" startDate="2026-09-12 07:01:00 -0700" endDate="2026-09-12 07:01:00 -0700" value="0.181"/>
              <Record type="HKCategoryTypeIdentifierSleepAnalysis" sourceName="Apple Watch" startDate="2026-09-11 23:00:00 -0700" endDate="2026-09-12 06:30:00 -0700" value="HKCategoryValueSleepAnalysisAsleepCore"/>
              <Workout workoutActivityType="HKWorkoutActivityTypeRunning" sourceName="Apple Watch" startDate="2026-09-12 18:00:00 -0700" duration="30" durationUnit="min" totalDistance="5" totalDistanceUnit="km" totalEnergyBurned="400" totalEnergyBurnedUnit="kcal">
                <WorkoutStatistics type="HKQuantityTypeIdentifierHeartRate" average="144" minimum="90" maximum="178" unit="count/min"/>
              </Workout>
            </HealthData>
            """
        )
    )

    first = backfill_xml(xml, db, batch_size=2)
    second = backfill_xml(xml, db, batch_size=2)
    assert first["delta"]["resting_hr"] == 1
    assert first["delta"]["body_comp_samples"] == 1
    assert first["delta"]["sleep_segments"] == 1
    assert first["delta"]["workouts"] == 1
    assert second["delta"]["resting_hr"] == 0
    assert second["delta"]["body_comp_samples"] == 0

    conn = connect(db)
    try:
        assert table_count(conn, "apple_xml_backfills") == 2
    finally:
        conn.close()
