from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import duckdb

from core.schema import DEFAULT_DB, connect, load_schema, quote_ident

VANCOUVER = ZoneInfo("America/Vancouver")


@dataclass(frozen=True)
class UpsertResult:
    stream: str
    table: str
    rows_seen: int
    inserted: int
    updated: int
    min_ts: str | None
    max_ts: str | None

    @property
    def rows_upserted(self) -> int:
        return self.inserted + self.updated


BODY_COMP_TYPES = {
    "weight_body_mass": "weight_kg",
    "body_fat_percentage": "body_fat_pct",
    "lean_body_mass": "lean_mass_kg",
}

DAILY_METRIC_COLUMNS = {
    "step_count": "steps",
    "walking_speed": "walk_speed_kmh",
    "walking_step_length": "walk_stride_cm",
    "walking_double_support_percentage": "double_support_pct",
    "walking_asymmetry_percentage": "asymmetry_pct",
    "stair_speed_up": "stair_up_speed",
    "stair_speed_down": "stair_down_speed",
    "respiratory_rate": "resp_rate",
    "time_in_daylight": "daylight_min",
    "active_energy": "active_cal",
    "basal_energy_burned": "basal_cal",
    "apple_exercise_time": "exercise_min",
    "apple_stand_time": "stand_min",
    "flights_climbed": "flights",
    "physical_effort": "physical_effort",
    "running_speed": "run_speed_kmh",
    "running_power": "run_power_w",
    "running_ground_contact_time": "run_gct_ms",
    "running_stride_length": "run_stride_cm",
    "running_vertical_oscillation": "run_vert_osc_cm",
    "environmental_audio_exposure": "env_audio_db",
    "headphone_audio_exposure": "headphone_db",
}

DAILY_SUM_METRICS = {
    "step_count",
    "time_in_daylight",
    "active_energy",
    "basal_energy_burned",
    "apple_exercise_time",
    "apple_stand_time",
    "flights_climbed",
}


def ingest_hae_payload(
    payload: dict[str, Any],
    db_path: str | Path = DEFAULT_DB,
    source_prefix: str = "hae",
    append_only_after_existing_max: bool = False,
) -> dict[str, Any]:
    conn = connect(db_path)
    try:
        load_schema(conn)
        ingestor = HaeIngestor(conn, source_prefix, append_only_after_existing_max)
        results = ingestor.ingest_payload(payload)
        return {
            "ok": True,
            "source_prefix": source_prefix,
            "streams": {r.stream: result_payload(r) for r in results},
            "rows_seen": sum(r.rows_seen for r in results),
            "rows_upserted": sum(r.rows_upserted for r in results),
            "inserted": sum(r.inserted for r in results),
            "updated": sum(r.updated for r in results),
        }
    finally:
        conn.close()


class HaeIngestor:
    def __init__(self, conn: duckdb.DuckDBPyConnection, source_prefix: str = "hae", append_only_after_existing_max: bool = False):
        self.conn = conn
        self.source_prefix = source_prefix
        self.append_only = append_only_after_existing_max
        self.cutoffs = self._load_cutoffs() if append_only_after_existing_max else {}

    def ingest_payload(self, payload: dict[str, Any]) -> list[UpsertResult]:
        data = payload.get("data", payload)
        metrics = data.get("metrics", [])
        workouts = data.get("workouts", [])
        results: list[UpsertResult] = []

        heart_rows: list[dict[str, Any]] = []
        sleep_rows: list[dict[str, Any]] = []
        daily_rows: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        daily_seen: dict[str, set[str]] = defaultdict(set)

        for metric in metrics:
            name = normalize_name(metric.get("name"))
            units = metric.get("units") or metric.get("unit") or ""
            rows = metric.get("data") or []
            if not name or not isinstance(rows, list):
                continue

            if name == "heart_rate":
                heart_rows.extend(normalize_heart_rate_rows(rows, units))
            elif name == "heart_rate_variability":
                results.append(self._upsert_simple_samples("hrv_samples", "hrv", rows, units, "hrv_ms", convert_passthrough))
            elif name == "resting_heart_rate":
                results.append(self._upsert_daily_scalar("resting_hr", "resting_hr", rows, units, "resting_hr", convert_passthrough, as_int=True))
            elif name == "vo2_max":
                results.append(self._upsert_daily_scalar("vo2max", "vo2max", rows, units, "vo2max", convert_passthrough))
            elif name == "blood_oxygen_saturation":
                results.append(self._upsert_simple_samples("spo2_samples", "spo2", rows, units, "spo2_pct", convert_percent))
            elif name == "sleep_analysis":
                sleep_rows.extend(normalize_sleep_rows(rows, units))
            elif name in BODY_COMP_TYPES:
                results.append(self._upsert_body_comp(name, rows, units))
            elif name in DAILY_METRIC_COLUMNS:
                for row in rows:
                    parsed = parse_datetime(any_key(row, "date", "startDate", "start", "time"))
                    if parsed is None:
                        continue
                    day = parsed.date().isoformat()
                    value = convert_daily_metric(name, scalar_value(row), units)
                    if value is None:
                        continue
                    daily_rows[day][DAILY_METRIC_COLUMNS[name]].append(value)
                    daily_seen[day].add(name)

        if heart_rows:
            results.append(self._upsert_heart_hourly(heart_rows))
        if sleep_rows:
            results.append(self._upsert_sleep(sleep_rows))
        if daily_rows:
            results.append(self._upsert_daily_metrics(daily_rows, daily_seen))
        if isinstance(workouts, list) and workouts:
            results.append(self._upsert_workouts(workouts))

        for result in results:
            self._log_result(result, payload)
        return results

    def _load_cutoffs(self) -> dict[str, Any]:
        cutoffs: dict[str, Any] = {}
        for table, column in {
            "resting_hr": "date",
            "vo2max": "date",
            "hrv_samples": "ts",
            "spo2_samples": "ts",
            "hr_hourly": "hour",
            "daily_metrics": "date",
            "workouts": "start_ts",
            "body_comp_samples": "date",
            "sleep_segments": "start_ts",
        }.items():
            value = self.conn.execute(f"SELECT MAX({quote_ident(column)}) FROM {quote_ident(table)}").fetchone()[0]
            if value is not None:
                cutoffs[table] = value
        return cutoffs

    def _passes_cutoff(self, table: str, value: Any) -> bool:
        cutoff = self.cutoffs.get(table)
        if cutoff is None:
            return True
        return value > cutoff

    def _upsert_simple_samples(self, table: str, stream: str, rows: list[dict[str, Any]], units: str, value_col: str, converter) -> UpsertResult:
        normalized = []
        for row in rows:
            ts = parse_datetime(any_key(row, "date", "startDate", "start", "time"))
            value = converter(scalar_value(row), units)
            if ts is None or value is None or not self._passes_cutoff(table, ts):
                continue
            normalized.append({
                "import_id": stable_id(self.source_prefix, table, ts.isoformat(), row.get("source") or "apple_watch"),
                "ts": ts,
                value_col: value,
                **({"source": row.get("source") or "apple_watch"} if table == "hrv_samples" else {}),
            })
        return self._replace_rows(table, stream, normalized, ("import_id",), ("ts",), rows_seen=len(rows))

    def _upsert_daily_scalar(self, table: str, stream: str, rows: list[dict[str, Any]], units: str, value_col: str, converter, as_int: bool = False) -> UpsertResult:
        by_day: dict[date, float] = {}
        for row in rows:
            ts = parse_datetime(any_key(row, "date", "startDate", "start", "time"))
            value = converter(scalar_value(row), units)
            if ts is None or value is None:
                continue
            day = ts.date()
            if not self._passes_cutoff(table, day):
                continue
            by_day[day] = int(round(value)) if as_int else value
        normalized = [{"import_id": stable_id(self.source_prefix, table, day.isoformat()), "date": day, value_col: value} for day, value in sorted(by_day.items())]
        return self._replace_rows(table, stream, normalized, ("import_id",), ("date",), rows_seen=len(rows))

    def _upsert_body_comp(self, metric_name: str, rows: list[dict[str, Any]], units: str) -> UpsertResult:
        normalized = []
        metric_type = BODY_COMP_TYPES[metric_name]
        for row in rows:
            ts = parse_datetime(any_key(row, "date", "startDate", "start", "time"))
            if ts is None:
                continue
            day = ts.date()
            if not self._passes_cutoff("body_comp_samples", day):
                continue
            source = row.get("source") or row.get("Source") or "Health Auto Export"
            value = scalar_value(row)
            if metric_type == "body_fat_pct":
                value = convert_percent(value, units)
            else:
                value = convert_mass(value, units)
            if value is None:
                continue
            normalized.append({
                "import_id": stable_id(self.source_prefix, "body_comp_samples", day.isoformat(), metric_type, source),
                "date": day,
                "type": metric_type,
                "value": value,
                "source": source,
            })
        return self._replace_rows("body_comp_samples", f"body_comp:{metric_type}", normalized, ("import_id",), ("date",), rows_seen=len(rows))

    def _upsert_heart_hourly(self, rows: list[dict[str, Any]]) -> UpsertResult:
        buckets: dict[datetime, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            ts = row["ts"].replace(minute=0, second=0, microsecond=0)
            if self._passes_cutoff("hr_hourly", ts):
                buckets[ts].append(row)

        normalized = []
        for hour, values in sorted(buckets.items()):
            avgs = [v["avg"] for v in values if v["avg"] is not None]
            mins = [v["min"] for v in values if v["min"] is not None]
            maxs = [v["max"] for v in values if v["max"] is not None]
            samples = sum(v["samples"] for v in values)
            if not avgs:
                continue
            normalized.append({
                "import_id": stable_id(self.source_prefix, "hr_hourly", hour.isoformat()),
                "hour": hour,
                "hr_avg": int(round(sum(avgs) / len(avgs))),
                "hr_min": int(round(min(mins or avgs))),
                "hr_max": int(round(max(maxs or avgs))),
                "samples": int(samples or len(avgs)),
            })
        return self._replace_rows("hr_hourly", "hr_hourly", normalized, ("import_id",), ("hour",), rows_seen=len(rows))

    def _upsert_sleep(self, rows: list[dict[str, Any]]) -> UpsertResult:
        normalized = []
        for row in rows:
            start = row["start_ts"]
            if not self._passes_cutoff("sleep_segments", start):
                continue
            normalized.append({
                "import_id": stable_id(self.source_prefix, "sleep_segments", start.isoformat(), row["end_ts"].isoformat(), row["value"], row["source"]),
                **row,
            })
        return self._replace_rows("sleep_segments", "sleep_segments", normalized, ("import_id",), ("start_ts", "end_ts"), rows_seen=len(rows))

    def _upsert_daily_metrics(self, daily_rows: dict[str, dict[str, list[float]]], daily_seen: dict[str, set[str]]) -> UpsertResult:
        inserted = 0
        updated = 0
        dates: list[date] = []
        for day_s, cols in sorted(daily_rows.items()):
            day = datetime.strptime(day_s, "%Y-%m-%d").date()
            if not self._passes_cutoff("daily_metrics", day):
                continue
            import_id = stable_id(self.source_prefix, "daily_metrics", day_s)
            dates.append(day)
            exists = self.conn.execute("SELECT 1 FROM daily_metrics WHERE import_id = ?", [import_id]).fetchone() is not None
            if not exists:
                self.conn.execute("INSERT INTO daily_metrics (import_id, date) VALUES (?, ?)", [import_id, day])
                inserted += 1
            assignments = []
            params: list[Any] = []
            for column, values in cols.items():
                source_metric = next((name for name, col in DAILY_METRIC_COLUMNS.items() if col == column and name in daily_seen[day_s]), "")
                value = sum(values) if source_metric in DAILY_SUM_METRICS else sum(values) / len(values)
                assignments.append(f"{quote_ident(column)} = ?")
                params.append(value)
            if assignments:
                params.append(import_id)
                self.conn.execute(f"UPDATE daily_metrics SET {', '.join(assignments)} WHERE import_id = ?", params)
                if exists:
                    updated += 1
        return UpsertResult("daily_metrics", "daily_metrics", sum(len(names) for names in daily_seen.values()), inserted, updated, minmax_iso(dates, 0), minmax_iso(dates, -1))

    def _upsert_workouts(self, workouts: list[dict[str, Any]]) -> UpsertResult:
        normalized = []
        for idx, workout in enumerate(workouts):
            start = parse_datetime(any_key(workout, "date", "startDate", "start", "start_ts"))
            if start is None or not self._passes_cutoff("workouts", start):
                continue
            kind = any_key(workout, "type", "name", "workoutActivityType") or "Workout"
            source = any_key(workout, "source", "Source") or "Health Auto Export"
            duration = convert_time(any_key(workout, "duration_min", "duration", "durationMinutes"), any_key(workout, "durationUnit", "duration_units") or "min")
            distance = convert_distance(any_key(workout, "distance_km", "distance", "totalDistance"), any_key(workout, "distanceUnit", "distance_units") or "km")
            calories = convert_energy(any_key(workout, "calories", "activeEnergy", "totalEnergyBurned"), any_key(workout, "energyUnit", "calorieUnit") or "kcal")
            hr_avg = to_float(any_key(workout, "hr_avg", "averageHeartRate", "Avg"))
            hr_min = to_float(any_key(workout, "hr_min", "minimumHeartRate", "Min"))
            hr_max = to_float(any_key(workout, "hr_max", "maximumHeartRate", "Max"))
            workout_id = str(any_key(workout, "workout_id", "id", "uuid") or stable_id(self.source_prefix, "workout", start.isoformat(), kind, duration, idx))
            normalized.append({
                "import_id": stable_id(self.source_prefix, "workouts", workout_id),
                "workout_id": workout_id,
                "start_ts": start,
                "type": normalize_workout_type(str(kind)),
                "duration_min": duration,
                "distance_km": distance or 0.0,
                "calories": int(round(calories or 0)),
                "hr_avg": int(round(hr_avg or 0)),
                "hr_min": int(round(hr_min or 0)),
                "hr_max": int(round(hr_max or 0)),
                "source": source,
                "trimp": None,
                "srpe_load": None,
                "session_rpe": None,
            })
        return self._replace_rows("workouts", "workouts", normalized, ("import_id",), ("start_ts",), rows_seen=len(workouts))

    def _replace_rows(self, table: str, stream: str, rows: list[dict[str, Any]], key_columns: tuple[str, ...], range_columns: tuple[str, ...], rows_seen: int) -> UpsertResult:
        if not rows:
            return UpsertResult(stream, table, rows_seen, 0, 0, None, None)
        rows_by_key = {tuple(row[col] for col in key_columns): row for row in rows}
        rows = list(rows_by_key.values())
        existing = 0
        for row in rows:
            where = " AND ".join(f"{quote_ident(col)} = ?" for col in key_columns)
            params = [row[col] for col in key_columns]
            if self.conn.execute(f"SELECT 1 FROM {quote_ident(table)} WHERE {where}", params).fetchone() is not None:
                existing += 1
            self.conn.execute(f"DELETE FROM {quote_ident(table)} WHERE {where}", params)
        columns = tuple(rows[0].keys())
        column_sql = ", ".join(quote_ident(c) for c in columns)
        placeholders = ", ".join("?" for _ in columns)
        self.conn.executemany(
            f"INSERT INTO {quote_ident(table)} ({column_sql}) VALUES ({placeholders})",
            [[row.get(c) for c in columns] for row in rows],
        )
        range_values = [row[col] for row in rows for col in range_columns if row.get(col) is not None]
        return UpsertResult(stream, table, rows_seen, len(rows) - existing, existing, minmax_iso(range_values, 0), minmax_iso(range_values, -1))

    def _log_result(self, result: UpsertResult, payload: dict[str, Any]) -> None:
        if result.rows_seen == 0:
            return
        self.conn.execute(
            """
            INSERT INTO ingest_log (received_at, source, payload_hash, rows_upserted, min_ts, max_ts)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                datetime.now(timezone.utc).replace(tzinfo=None),
                f"{self.source_prefix}:{result.stream}",
                hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest(),
                result.rows_upserted,
                result.min_ts,
                result.max_ts,
            ],
        )


def normalize_heart_rate_rows(rows: list[dict[str, Any]], units: str) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        ts = parse_datetime(any_key(row, "date", "startDate", "start", "time"))
        if ts is None:
            continue
        avg = convert_passthrough(any_key(row, "Avg", "avg", "qty", "value"), units)
        low = convert_passthrough(any_key(row, "Min", "min", "minimum"), units)
        high = convert_passthrough(any_key(row, "Max", "max", "maximum"), units)
        count = to_float(any_key(row, "samples", "count", "Count")) or 1
        normalized.append({"ts": ts, "avg": avg, "min": low or avg, "max": high or avg, "samples": int(count)})
    return normalized


def normalize_sleep_rows(rows: list[dict[str, Any]], units: str) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        start = parse_datetime(any_key(row, "start", "startDate", "date"))
        end = parse_datetime(any_key(row, "end", "endDate", "finish"))
        value = any_key(row, "value", "stage", "sleepStage", "name") or "HKCategoryValueSleepAnalysisAsleepUnspecified"
        source = any_key(row, "source", "Source") or "Health Auto Export"
        if start is None or end is None:
            continue
        normalized.append({"start_ts": start, "end_ts": end, "value": normalize_sleep_value(str(value)), "source": source})
    return normalized


def normalize_sleep_value(value: str) -> str:
    if value.startswith("HKCategoryValueSleepAnalysis"):
        return value
    compact = value.strip().lower().replace(" ", "")
    mapping = {
        "inbed": "HKCategoryValueSleepAnalysisInBed",
        "awake": "HKCategoryValueSleepAnalysisAwake",
        "asleep": "HKCategoryValueSleepAnalysisAsleepUnspecified",
        "asleepcore": "HKCategoryValueSleepAnalysisAsleepCore",
        "core": "HKCategoryValueSleepAnalysisAsleepCore",
        "asleeprem": "HKCategoryValueSleepAnalysisAsleepREM",
        "rem": "HKCategoryValueSleepAnalysisAsleepREM",
        "asleepdeep": "HKCategoryValueSleepAnalysisAsleepDeep",
        "deep": "HKCategoryValueSleepAnalysisAsleepDeep",
        "asleepunspecified": "HKCategoryValueSleepAnalysisAsleepUnspecified",
    }
    return mapping.get(compact, value)


def normalize_workout_type(value: str) -> str:
    value = value.replace("HKWorkoutActivityType", "")
    if not value:
        return "Workout"
    return value[0].upper() + value[1:]


def normalize_name(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def any_key(row: dict[str, Any], *keys: str) -> Any:
    lower = {str(k).lower(): v for k, v in row.items()}
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
        found = lower.get(key.lower())
        if found not in (None, ""):
            return found
    return None


def scalar_value(row: dict[str, Any]) -> Any:
    return any_key(row, "qty", "value", "Value", "Avg", "avg", "sum", "Sum")


def parse_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S%z", "%Y-%m-%dT%H:%M:%S %z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.astimezone(VANCOUVER).replace(tzinfo=None)
        except ValueError:
            pass
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    if " " in text and "T" not in text:
        text = text.replace(" ", "T", 1)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M", "%Y-%m-%dT%H:%M:%S"):
            try:
                parsed = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(VANCOUVER).replace(tzinfo=None)
    return parsed


def convert_daily_metric(name: str, value: Any, units: str) -> float | None:
    if name in {"walking_double_support_percentage", "walking_asymmetry_percentage"}:
        return convert_percent(value, units)
    if name in {"walking_speed", "stair_speed_up", "stair_speed_down", "running_speed"}:
        return convert_speed(value, units)
    if name in {"walking_step_length", "running_stride_length", "running_vertical_oscillation"}:
        return convert_length(value, units)
    if name in {"active_energy", "basal_energy_burned"}:
        return convert_energy(value, units)
    if name in {"apple_exercise_time", "apple_stand_time", "time_in_daylight"}:
        return convert_time(value, units)
    return convert_passthrough(value, units)


def convert_passthrough(value: Any, units: str = "") -> float | None:
    return to_float(value)


def convert_percent(value: Any, units: str = "") -> float | None:
    number = to_float(value)
    if number is None:
        return None
    unit = units.lower().strip()
    if number <= 1 and unit in {"", "%", "percent", "percentage", "count"}:
        return number * 100
    return number


def convert_mass(value: Any, units: str = "") -> float | None:
    number = to_float(value)
    if number is None:
        return None
    unit = units.lower().strip()
    if unit in {"lb", "lbs", "pound", "pounds"}:
        return number * 0.45359237
    if unit in {"g", "gram", "grams"}:
        return number / 1000
    return number


def convert_distance(value: Any, units: str = "") -> float | None:
    number = to_float(value)
    if number is None:
        return None
    unit = units.lower().strip()
    if unit in {"m", "meter", "meters"}:
        return number / 1000
    if unit in {"mi", "mile", "miles"}:
        return number * 1.609344
    return number


def convert_speed(value: Any, units: str = "") -> float | None:
    number = to_float(value)
    if number is None:
        return None
    unit = units.lower().replace(" ", "").strip()
    if unit in {"mph", "mi/h", "mile/h", "miles/hour", "milesperhour"}:
        return number * 1.609344
    if unit in {"m/s", "meter/s", "meters/second", "meterspersecond"}:
        return number * 3.6
    return number


def convert_length(value: Any, units: str = "") -> float | None:
    number = to_float(value)
    if number is None:
        return None
    unit = units.lower().strip()
    if unit in {"m", "meter", "meters"}:
        return number * 100
    if unit in {"mm", "millimeter", "millimeters"}:
        return number / 10
    if unit in {"in", "inch", "inches"}:
        return number * 2.54
    return number


def convert_energy(value: Any, units: str = "") -> float | None:
    number = to_float(value)
    if number is None:
        return None
    unit = units.lower().strip()
    if unit in {"kj", "kilojoule", "kilojoules"}:
        return number / 4.184
    if unit in {"j", "joule", "joules"}:
        return number / 4184
    return number


def convert_time(value: Any, units: str = "") -> float | None:
    number = to_float(value)
    if number is None:
        return None
    unit = units.lower().strip()
    if unit in {"s", "sec", "second", "seconds"}:
        return number / 60
    if unit in {"h", "hr", "hour", "hours"}:
        return number * 60
    return number


def to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def stable_id(*parts: Any) -> str:
    text = "|".join(str(part) for part in parts)
    return hashlib.sha256(text.encode()).hexdigest()


def minmax_iso(values: Iterable[Any], index: int) -> str | None:
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    value = values[index]
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def result_payload(result: UpsertResult) -> dict[str, Any]:
    return {
        "table": result.table,
        "rows_seen": result.rows_seen,
        "inserted": result.inserted,
        "updated": result.updated,
        "rows_upserted": result.rows_upserted,
        "min_ts": result.min_ts,
        "max_ts": result.max_ts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a Health Auto Export JSON payload.")
    parser.add_argument("payload", type=Path)
    parser.add_argument("--db", default=str(DEFAULT_DB))
    args = parser.parse_args()
    print(json.dumps(ingest_hae_payload(json.loads(args.payload.read_text()), args.db), indent=2))


if __name__ == "__main__":
    main()
