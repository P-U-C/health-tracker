from __future__ import annotations

from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = REPO_ROOT / "data" / "health.duckdb"
SCHEMA_SQL = REPO_ROOT / "schema" / "schema.sql"


def connect(db_path: str | Path = DEFAULT_DB) -> duckdb.DuckDBPyConnection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(path))


def load_schema(conn: duckdb.DuckDBPyConnection, schema_path: str | Path = SCHEMA_SQL) -> None:
    conn.execute(Path(schema_path).read_text())
    ensure_migrations(conn)


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def table_count(conn: duckdb.DuckDBPyConnection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {quote_ident(table)}").fetchone()[0])


def ensure_migrations(conn: duckdb.DuckDBPyConnection) -> None:
    columns = {
        row[1]
        for row in conn.execute("PRAGMA table_info('dexa_regional')").fetchall()
    }
    if "import_id" not in columns:
        conn.execute("ALTER TABLE dexa_regional ADD COLUMN import_id TEXT")
