from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

from core.contracts import ALL_CONTRACTS, REPO_ROOT, TABLE_BY_PATH, CsvContract, insert_columns, load_source_dataframe
from core.schema import connect, load_schema, quote_ident, table_count

MANIFEST = REPO_ROOT / "data" / "manifest.json"


def ingest_all(db_path: str | Path = REPO_ROOT / "data" / "health.duckdb", root: Path = REPO_ROOT) -> dict[str, int]:
    conn = connect(db_path)
    try:
        load_schema(conn)
        inserted: dict[str, int] = {}
        for contract in ALL_CONTRACTS:
            df = load_source_dataframe(contract, root)
            inserted[contract.source_rel] = insert_contract(conn, contract, df)
            log_ingest(conn, contract, root / contract.source_rel, inserted[contract.source_rel], df)
        return inserted
    finally:
        conn.close()


def insert_contract(conn: duckdb.DuckDBPyConnection, contract: CsvContract, df) -> int:
    before = table_count(conn, contract.table)
    columns = insert_columns(contract)
    stage_name = "_stage_import"
    conn.register(stage_name, df[list(columns)])
    column_sql = ", ".join(quote_ident(c) for c in columns)
    select_sql = ", ".join(f"s.{quote_ident(c)}" for c in columns)
    where_sql = " AND ".join(
        f"t.{quote_ident(col)} = s.{quote_ident(col)}" for col in contract.key_columns
    )
    if "import_id" in columns and contract.key_columns != ("import_id",):
        update_where = " AND ".join(
            f"t.{quote_ident(col)} = s.{quote_ident(col)}" for col in contract.key_columns
        )
        conn.execute(
            f"""
            UPDATE {quote_ident(contract.table)} AS t
            SET import_id = s.import_id
            FROM {stage_name} s
            WHERE {update_where} AND t.import_id IS NULL
            """
        )
    conn.execute(
        f"""
        INSERT INTO {quote_ident(contract.table)} ({column_sql})
        SELECT {select_sql}
        FROM {stage_name} s
        WHERE NOT EXISTS (
          SELECT 1 FROM {quote_ident(contract.table)} t WHERE {where_sql}
        )
        """
    )
    conn.unregister(stage_name)
    return table_count(conn, contract.table) - before


def log_ingest(conn: duckdb.DuckDBPyConnection, contract: CsvContract, source: Path, rows: int, df) -> None:
    first_db_col = next(
        (col for col in ("date", "ts", "hour", "start_ts", "scan_date") if col in df.columns),
        contract.db_columns[0],
    )
    min_ts = None
    max_ts = None
    if first_db_col in df.columns and len(df):
        series = df[first_db_col].dropna()
        if len(series):
            min_ts = str(series.min())
            max_ts = str(series.max())
    payload_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    conn.execute(
        """
        INSERT INTO ingest_log (received_at, source, payload_hash, rows_upserted, min_ts, max_ts)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            datetime.now(timezone.utc).replace(tzinfo=None),
            contract.source_rel,
            payload_hash,
            rows,
            min_ts,
            max_ts,
        ],
    )


def validate_manifest_counts(db_path: str | Path = REPO_ROOT / "data" / "health.duckdb", root: Path = REPO_ROOT) -> list[dict[str, object]]:
    manifest = json.loads((root / "data" / "manifest.json").read_text())
    conn = connect(db_path)
    try:
        rows = []
        for item in manifest["files"]:
            if "rows" not in item:
                continue
            path = item["path"]
            table = TABLE_BY_PATH[path]
            actual = table_count(conn, table)
            rows.append({"path": path, "table": table, "expected": int(item["rows"]), "actual": actual, "ok": actual == int(item["rows"])})
        return rows
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Load package CSVs and DEXA summaries into DuckDB.")
    parser.add_argument("--db", default=str(REPO_ROOT / "data" / "health.duckdb"))
    args = parser.parse_args()
    inserted = ingest_all(args.db)
    counts = validate_manifest_counts(args.db)
    mismatches = [row for row in counts if not row["ok"]]
    print(json.dumps({"inserted": inserted, "manifest_counts": counts, "mismatches": mismatches}, indent=2))
    if mismatches:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
