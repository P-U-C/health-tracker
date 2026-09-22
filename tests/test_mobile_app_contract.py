from __future__ import annotations

from pathlib import Path

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
    assert today["next_action"]["title"]
    assert any(item["id"] == "confirm-phase" for item in today["not_done_today"])
    assert any(item["id"] == "strength-log" for item in today["not_done_today"])
    assert today["capture"]["write_status"] == "planned"
    assert "context_packet" in today["review_links"]


def test_mobile_context_packet_is_chat_ready(tmp_path: Path) -> None:
    db = tmp_path / "health.duckdb"
    _seed_mobile_db(db)

    packet = build_context_packet(db)

    assert packet.startswith("# Health Context Packet")
    assert "## Current Phase" in packet
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
