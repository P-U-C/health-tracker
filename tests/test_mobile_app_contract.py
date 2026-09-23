from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from api.app import app
from core.mobile import build_context_packet, build_today_model
from core.schema import connect, load_schema
from ingest.hae_rest import ingest_hae_payload
from tests.test_phase2_pipe import sample_hae_payload


def _seed_mobile_db(db: Path) -> None:
    ingest_hae_payload(sample_hae_payload(), db)
    conn = connect(db)
    try:
        load_schema(conn)
        conn.execute(
            """
            INSERT INTO dexa_scans (
              scan_number, scan_date, provider, weight_kg, fat_mass_kg, lean_bmc_kg,
              body_fat_pct, vat_mass_g, android_gynoid_ratio, bmd_total_g_cm2
            ) VALUES
              (1, DATE '2026-02-26', 'Test DEXA', 70.93, 12.91, 58.02, 18.2, 333, 1.30, 1.218),
              (2, DATE '2026-09-12', 'Test DEXA', 81.65, 13.88, 67.77, 17.0, 250, 1.05, 1.18)
            """
        )
    finally:
        conn.close()


def test_mobile_today_contract_prioritizes_protocol_actions(tmp_path: Path) -> None:
    db = tmp_path / "health.duckdb"
    _seed_mobile_db(db)

    today = build_today_model(db)

    assert today["overall"]["state"] in {"On track", "Watch", "Action required", "Insufficient data"}
    assert today["phase"]["title"] == "Post-fast body-composition stint"
    assert today["progress"]["primary_label"] == "7-day weight trend"
    assert today["progress"]["target_label"] == "70.5-71.5 kg"
    assert today["body"]["summary"]["latest_dexa_date"] == "2026-09-12"
    assert today["body"]["summary"]["body_fat_pct"] == 17.0
    assert today["body"]["summary"]["lean_bmc_kg"] == 67.77
    assert today["body"]["summary"]["vat_mass_g"] == 250
    assert today["body"]["summary"]["dexa_count"] == 2
    assert {metric["key"] for metric in today["body"]["metrics"]} >= {"dexa_bf", "dexa_lean", "vat"}
    assert today["next_action"]["title"]
    assert any(item["id"] == "confirm-phase" for item in today["not_done_today"])
    assert any(item["id"] == "strength-log" for item in today["not_done_today"])
    assert today["capture"]["write_status"] == "enabled"
    assert today["capture"]["endpoint"] == "/api/mobile/capture"
    assert today["capture"]["auth_required"] is True
    assert "context_packet" in today["review_links"]


def test_mobile_context_packet_is_chat_ready(tmp_path: Path) -> None:
    db = tmp_path / "health.duckdb"
    _seed_mobile_db(db)

    packet = build_context_packet(db)

    assert packet.startswith("# Health Context Packet")
    assert "## Current Phase" in packet
    assert "## Body Composition" in packet
    assert "DEXA body fat: 17.0 %" in packet
    assert "## Not Done Today" in packet
    assert "## Active Tripwire" in packet
    assert "Use deterministic tripwires as authority" in packet


def test_mobile_api_routes_return_today_and_context(tmp_path: Path, monkeypatch) -> None:
    db = tmp_path / "health.duckdb"
    _seed_mobile_db(db)
    monkeypatch.setenv("HEALTH_DB", str(db))

    client = TestClient(app)
    today_response = client.get("/api/mobile/today")
    context_response = client.get("/api/mobile/context")

    assert today_response.status_code == 200
    today = today_response.json()
    assert today["phase"]["title"] == "Post-fast body-composition stint"
    assert today["capture"]["primary_prompt"] == "What happened today?"

    assert context_response.status_code == 200
    context = context_response.json()
    assert context["format"] == "markdown"
    assert "# Health Context Packet" in context["markdown"]


def test_mobile_pwa_routes_render_installable_shell(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HEALTH_DB", str(tmp_path / "health.duckdb"))
    client = TestClient(app)

    app_response = client.get("/app")
    manifest_response = client.get("/app/manifest.webmanifest")
    worker_response = client.get("/app/service-worker.js")
    icon_response = client.get("/app/icon.svg")

    assert app_response.status_code == 200
    assert "Health" in app_response.text
    assert "viewport-fit=cover" in app_response.text
    assert "height: 100dvh" in app_response.text
    assert "data-tab=\"body\"" in app_response.text
    assert "data-tab=\"capture\"" in app_response.text
    assert "renderBody" in app_response.text
    assert "aria-label=\"Log health note\"" in app_response.text
    assert "service-worker.js?v=3" in app_response.text
    assert "Unlock capture" in app_response.text
    assert manifest_response.status_code == 200
    assert manifest_response.json()["display"] == "standalone"
    assert worker_response.status_code == 200
    assert "health-companion-v3" in worker_response.text
    assert icon_response.status_code == 200
    assert "<svg" in icon_response.text


def test_mobile_session_cookie_unlocks_capture(tmp_path: Path, monkeypatch) -> None:
    db = tmp_path / "health.duckdb"
    _seed_mobile_db(db)
    monkeypatch.setenv("HEALTH_DB", str(db))
    monkeypatch.setenv("HEALTH_DASHBOARD_USER", "chad")
    monkeypatch.setenv("HEALTH_DASHBOARD_PASSWORD", "phone-pass")
    monkeypatch.delenv("HEALTH_APP_TOKEN", raising=False)
    monkeypatch.delenv("HEALTH_ALLOW_DEV_AUTH", raising=False)
    client = TestClient(app, base_url="https://testserver")

    denied = client.post("/api/mobile/capture", json={"intent": "event", "text": "Skipped swim"})
    login = client.post("/api/mobile/session", json={"username": "chad", "password": "phone-pass"})
    accepted = client.post("/api/mobile/capture", json={"intent": "event", "text": "Skipped swim"})

    assert denied.status_code == 401
    assert login.status_code == 200
    assert login.json()["authenticated"] is True
    assert accepted.status_code == 200
    assert accepted.json()["stored_as"] == "events"


def test_mobile_capture_requires_app_bearer(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HEALTH_DB", str(tmp_path / "health.duckdb"))
    monkeypatch.setenv("HEALTH_APP_TOKEN", "app-token")
    monkeypatch.delenv("HEALTH_ALLOW_DEV_AUTH", raising=False)
    client = TestClient(app)

    payload = {"intent": "event", "text": "Skipped swim; fatigue and heat"}

    assert client.post("/api/mobile/capture", json=payload).status_code == 401
    assert client.post("/api/mobile/capture", json=payload, headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert client.post("/api/mobile/capture", json=payload, headers={"Authorization": "Bearer app-token"}).status_code == 200


def test_mobile_capture_logs_strength_and_clears_strength_reminder(tmp_path: Path, monkeypatch) -> None:
    db = tmp_path / "health.duckdb"
    _seed_mobile_db(db)
    monkeypatch.setenv("HEALTH_DB", str(db))
    monkeypatch.setenv("HEALTH_APP_TOKEN", "app-token")
    client = TestClient(app)
    occurred_at = datetime.now(ZoneInfo("America/Vancouver")).replace(hour=10, minute=0, second=0, microsecond=0)

    response = client.post(
        "/api/mobile/capture",
        json={"intent": "strength_set", "text": "KB press 24 kg 3x8 RPE 8", "occurred_at": occurred_at.isoformat()},
        headers={"Authorization": "Bearer app-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["stored_as"] == "strength_sets"
    assert body["records_written"] == 3

    conn = connect(db)
    try:
        rows = conn.execute(
            """
            SELECT exercise, set_no, load_kg, reps, rpe
            FROM strength_sets
            WHERE session_date = ?
            ORDER BY set_no
            """,
            [occurred_at.date()],
        ).fetchall()
    finally:
        conn.close()
    assert rows == [("KB press", 1, 24.0, 8, 8.0), ("KB press", 2, 24.0, 8, 8.0), ("KB press", 3, 24.0, 8, 8.0)]

    today = build_today_model(db)
    assert not any(item["id"] == "strength-log" for item in today["not_done_today"])
    assert any(item["source"] == "strength_set" and item["title"] == "KB press" for item in today["recent_capture"])


def test_mobile_capture_logs_reading_and_override(tmp_path: Path, monkeypatch) -> None:
    db = tmp_path / "health.duckdb"
    _seed_mobile_db(db)
    monkeypatch.setenv("HEALTH_DB", str(db))
    monkeypatch.setenv("HEALTH_APP_TOKEN", "app-token")
    client = TestClient(app)

    reading_response = client.post(
        "/api/mobile/capture",
        json={"intent": "manual_reading", "text": "weight 81.2 kg"},
        headers={"Authorization": "Bearer app-token"},
    )
    override_response = client.post(
        "/api/mobile/capture",
        json={"intent": "override", "text": "Override: trained despite HRV strain"},
        headers={"Authorization": "Bearer app-token"},
    )

    assert reading_response.status_code == 200
    assert reading_response.json()["stored_as"] == "readings"
    assert override_response.status_code == 200
    assert override_response.json()["stored_as"] == "overrides"

    conn = connect(db)
    try:
        reading = conn.execute("SELECT metric, value, unit FROM readings WHERE source = 'ios'").fetchone()
        override_count = conn.execute("SELECT COUNT(*) FROM overrides").fetchone()[0]
    finally:
        conn.close()
    assert reading == ("weight", 81.2, "kg")
    assert override_count == 1
