from __future__ import annotations

import argparse
import csv
import io
from pathlib import Path
from typing import Any

import pandas as pd

from core.contracts import APPLE_CONTRACTS, ALL_CONTRACTS, REPO_ROOT, CsvContract, load_source_dataframe, project_export_frame
from core.schema import connect, quote_ident


def export_all(db_path: str | Path = REPO_ROOT / "data" / "health.duckdb", out_dir: str | Path = REPO_ROOT / "data" / "exports") -> dict[str, int]:
    out = Path(out_dir)
    conn = connect(db_path)
    written: dict[str, int] = {}
    try:
        for contract in ALL_CONTRACTS:
            df = read_export_frame(conn, contract)
            target = out / contract.export_rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(frame_to_csv_bytes(df, contract))
            written[contract.export_rel] = len(df)
        return written
    finally:
        conn.close()


def read_export_frame(conn, contract: CsvContract) -> pd.DataFrame:
    select_parts = []
    for export_col, db_col in zip(contract.export_columns, contract.db_columns):
        select_parts.append(f"{quote_ident(db_col)} AS {quote_ident(export_col)}")
    order_sql = ", ".join(quote_ident(c) for c in contract.order_by)
    return conn.execute(
        f"SELECT {', '.join(select_parts)} FROM {quote_ident(contract.table)} ORDER BY {order_sql}"
    ).fetchdf()


def normalized_source_bytes(contract: CsvContract, root: Path = REPO_ROOT) -> bytes:
    df = project_export_frame(load_source_dataframe(contract, root), contract)
    return frame_to_csv_bytes(df, contract)


def frame_to_csv_bytes(df: pd.DataFrame, contract: CsvContract) -> bytes:
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator=contract.line_terminator)
    writer.writerow(contract.export_columns)
    for _, row in df.iterrows():
        writer.writerow([format_cell(row[col], contract.format_kinds[col]) for col in contract.export_columns])
    return buf.getvalue().encode("utf-8")


def format_cell(value: Any, kind: str) -> str:
    if value is None or pd.isna(value):
        return ""
    if kind == "text":
        return str(value)
    if kind == "int":
        return str(int(value))
    if kind == "float":
        return str(float(value))
    if kind == "date":
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d")
        return str(value)[:10]
    if kind == "datetime_hour":
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d %H")
        return str(value)[:13]
    if kind == "datetime_minute":
        if hasattr(value, "strftime"):
            return value.strftime("%Y-%m-%d %H:%M")
        return str(value)[:16]
    raise ValueError(f"unknown format kind: {kind}")


def apple_contract_count() -> int:
    return len(APPLE_CONTRACTS)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export normalized CSV contracts from DuckDB.")
    parser.add_argument("--db", default=str(REPO_ROOT / "data" / "health.duckdb"))
    parser.add_argument("--out", default=str(REPO_ROOT / "data" / "exports"))
    args = parser.parse_args()
    written = export_all(args.db, args.out)
    for path, rows in written.items():
        print(f"{path}\t{rows}")


if __name__ == "__main__":
    main()
