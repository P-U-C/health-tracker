from __future__ import annotations

import csv
import json
from pathlib import Path

from core.contracts import ALL_CONTRACTS, APPLE_CONTRACTS, REPO_ROOT, TABLE_BY_PATH
from core.schema import connect, load_schema, table_count
from export.csv_contracts import export_all, normalized_source_bytes
from ingest.package_csvs import ingest_all, validate_manifest_counts


def test_schema_loads(tmp_path: Path) -> None:
    conn = connect(tmp_path / "health.duckdb")
    try:
        load_schema(conn)
        tables = {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    finally:
        conn.close()

    assert "resting_hr" in tables
    assert "dexa_scans" in tables
    assert "derived_daily" in tables
    assert "ingest_log" in tables


def test_phase1_manifest_counts_and_dexa_exit(tmp_path: Path) -> None:
    db = tmp_path / "health.duckdb"
    ingest_all(db)
    counts = validate_manifest_counts(db)
    assert counts
    assert all(row["ok"] for row in counts)

    conn = connect(db)
    try:
        assert table_count(conn, "dexa_scans") == 9
        assert table_count(conn, "dexa_regional") == 90
    finally:
        conn.close()


def test_export_reproduces_normalized_csv_contracts(tmp_path: Path) -> None:
    db = tmp_path / "health.duckdb"
    out = tmp_path / "exports"
    ingest_all(db)
    written = export_all(db, out)

    assert set(written) == {contract.export_rel for contract in ALL_CONTRACTS}
    assert len(APPLE_CONTRACTS) == 11
    for contract in ALL_CONTRACTS:
        exported = (out / contract.export_rel).read_bytes()
        assert exported == normalized_source_bytes(contract)


def test_manifest_source_files_have_expected_rows() -> None:
    manifest = json.loads((REPO_ROOT / "data" / "manifest.json").read_text())
    for item in manifest["files"]:
        if "rows" not in item:
            continue
        assert item["path"] in TABLE_BY_PATH
        with (REPO_ROOT / item["path"]).open(newline="") as fh:
            actual = sum(1 for _ in csv.DictReader(fh))
        assert actual == item["rows"]
