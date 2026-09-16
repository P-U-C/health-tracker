from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.schema import DEFAULT_DB, connect, load_schema, table_count
from ingest.hae_rest import ingest_hae_payload

RECORD_MAP = {
    "HKQuantityTypeIdentifierHeartRate": "heart_rate",
    "HKQuantityTypeIdentifierHeartRateVariabilitySDNN": "heart_rate_variability",
    "HKQuantityTypeIdentifierRestingHeartRate": "resting_heart_rate",
    "HKQuantityTypeIdentifierVO2Max": "vo2_max",
    "HKQuantityTypeIdentifierOxygenSaturation": "blood_oxygen_saturation",
    "HKQuantityTypeIdentifierBodyMass": "weight_body_mass",
    "HKQuantityTypeIdentifierBodyFatPercentage": "body_fat_percentage",
    "HKQuantityTypeIdentifierLeanBodyMass": "lean_body_mass",
    "HKQuantityTypeIdentifierStepCount": "step_count",
    "HKQuantityTypeIdentifierWalkingSpeed": "walking_speed",
    "HKQuantityTypeIdentifierWalkingStepLength": "walking_step_length",
    "HKQuantityTypeIdentifierWalkingDoubleSupportPercentage": "walking_double_support_percentage",
    "HKQuantityTypeIdentifierWalkingAsymmetryPercentage": "walking_asymmetry_percentage",
    "HKQuantityTypeIdentifierStairAscentSpeed": "stair_speed_up",
    "HKQuantityTypeIdentifierStairDescentSpeed": "stair_speed_down",
    "HKQuantityTypeIdentifierRespiratoryRate": "respiratory_rate",
    "HKQuantityTypeIdentifierTimeInDaylight": "time_in_daylight",
    "HKQuantityTypeIdentifierActiveEnergyBurned": "active_energy",
    "HKQuantityTypeIdentifierBasalEnergyBurned": "basal_energy_burned",
    "HKQuantityTypeIdentifierAppleExerciseTime": "apple_exercise_time",
    "HKQuantityTypeIdentifierAppleStandTime": "apple_stand_time",
    "HKQuantityTypeIdentifierFlightsClimbed": "flights_climbed",
    "HKQuantityTypeIdentifierPhysicalEffort": "physical_effort",
    "HKQuantityTypeIdentifierRunningSpeed": "running_speed",
    "HKQuantityTypeIdentifierRunningPower": "running_power",
    "HKQuantityTypeIdentifierRunningGroundContactTime": "running_ground_contact_time",
    "HKQuantityTypeIdentifierRunningStrideLength": "running_stride_length",
    "HKQuantityTypeIdentifierRunningVerticalOscillation": "running_vertical_oscillation",
    "HKQuantityTypeIdentifierEnvironmentalAudioExposure": "environmental_audio_exposure",
    "HKQuantityTypeIdentifierHeadphoneAudioExposure": "headphone_audio_exposure",
}

TABLES = (
    "resting_hr",
    "vo2max",
    "hrv_samples",
    "spo2_samples",
    "hr_hourly",
    "daily_metrics",
    "workouts",
    "body_comp_samples",
    "sleep_segments",
)


def backfill_xml(xml_path: Path, db_path: str | Path = DEFAULT_DB, batch_size: int = 5000) -> dict[str, Any]:
    conn = connect(db_path)
    try:
        load_schema(conn)
        before = {table: table_count(conn, table) for table in TABLES}
    finally:
        conn.close()

    started_at = datetime.now(timezone.utc).replace(tzinfo=None)
    aggregate: dict[str, Any] = {"rows_seen": 0, "rows_upserted": 0, "inserted": 0, "updated": 0, "streams": {}}
    batch_metrics: dict[str, dict[str, Any]] = {}
    batch_workouts: list[dict[str, Any]] = []
    seen = 0

    for _event, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag == "Record":
            row = record_to_metric(elem.attrib)
            if row:
                name, data = row
                metric = batch_metrics.setdefault(name, {"name": name, "units": data.pop("units", ""), "data": []})
                metric["data"].append(data)
                seen += 1
        elif elem.tag == "Workout":
            batch_workouts.append(workout_to_row(elem))
            seen += 1
        if seen >= batch_size:
            merge_summary(aggregate, flush_batch(batch_metrics, batch_workouts, db_path))
            batch_metrics = {}
            batch_workouts = []
            seen = 0
        elem.clear()

    merge_summary(aggregate, flush_batch(batch_metrics, batch_workouts, db_path))

    conn = connect(db_path)
    try:
        after = {table: table_count(conn, table) for table in TABLES}
        report = {
            "ok": True,
            "source_file": str(xml_path),
            "before": before,
            "after": after,
            "delta": {table: after[table] - before[table] for table in TABLES},
            "summary": aggregate,
        }
        conn.execute(
            """
            INSERT INTO apple_xml_backfills (run_id, source_file, started_at, finished_at, report_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                f"applexml:{started_at.isoformat()}",
                str(xml_path),
                started_at,
                datetime.now(timezone.utc).replace(tzinfo=None),
                json.dumps(report, sort_keys=True),
            ],
        )
        return report
    finally:
        conn.close()


def flush_batch(metrics: dict[str, dict[str, Any]], workouts: list[dict[str, Any]], db_path: str | Path) -> dict[str, Any]:
    if not metrics and not workouts:
        return {"rows_seen": 0, "rows_upserted": 0, "inserted": 0, "updated": 0, "streams": {}}
    return ingest_hae_payload(
        {"data": {"metrics": list(metrics.values()), "workouts": workouts}},
        db_path=db_path,
        source_prefix="applexml",
        append_only_after_existing_max=True,
    )


def merge_summary(total: dict[str, Any], part: dict[str, Any]) -> None:
    total["rows_seen"] += int(part.get("rows_seen", 0))
    total["rows_upserted"] += int(part.get("rows_upserted", 0))
    total["inserted"] += int(part.get("inserted", 0))
    total["updated"] += int(part.get("updated", 0))
    for stream, value in part.get("streams", {}).items():
        current = total["streams"].setdefault(stream, {"rows_seen": 0, "inserted": 0, "updated": 0, "rows_upserted": 0})
        for key in ("rows_seen", "inserted", "updated", "rows_upserted"):
            current[key] += int(value.get(key, 0))
        current["min_ts"] = min_text(current.get("min_ts"), value.get("min_ts"))
        current["max_ts"] = max_text(current.get("max_ts"), value.get("max_ts"))


def record_to_metric(attrs: dict[str, str]) -> tuple[str, dict[str, Any]] | None:
    record_type = attrs.get("type")
    if record_type == "HKCategoryTypeIdentifierSleepAnalysis":
        return "sleep_analysis", {
            "start": attrs.get("startDate"),
            "end": attrs.get("endDate"),
            "value": attrs.get("value"),
            "source": attrs.get("sourceName"),
            "units": "",
        }
    metric = RECORD_MAP.get(record_type or "")
    if metric is None:
        return None
    return metric, {
        "date": attrs.get("startDate") or attrs.get("creationDate"),
        "qty": attrs.get("value"),
        "source": attrs.get("sourceName"),
        "units": attrs.get("unit") or "",
    }


def workout_to_row(elem: ET.Element) -> dict[str, Any]:
    attrs = dict(elem.attrib)
    row: dict[str, Any] = {
        "date": attrs.get("startDate"),
        "type": attrs.get("workoutActivityType", "Workout"),
        "duration": attrs.get("duration"),
        "durationUnit": attrs.get("durationUnit", "min"),
        "distance": attrs.get("totalDistance"),
        "distanceUnit": attrs.get("totalDistanceUnit", "km"),
        "calories": attrs.get("totalEnergyBurned"),
        "energyUnit": attrs.get("totalEnergyBurnedUnit", "kcal"),
        "source": attrs.get("sourceName"),
    }
    for child in elem:
        if child.tag != "WorkoutStatistics":
            continue
        stat_type = child.attrib.get("type", "")
        if stat_type == "HKQuantityTypeIdentifierHeartRate":
            row["hr_avg"] = child.attrib.get("average")
            row["hr_min"] = child.attrib.get("minimum")
            row["hr_max"] = child.attrib.get("maximum")
        elif stat_type in {"HKQuantityTypeIdentifierDistanceWalkingRunning", "HKQuantityTypeIdentifierDistanceCycling", "HKQuantityTypeIdentifierDistanceSwimming"}:
            row["distance"] = child.attrib.get("sum") or row.get("distance")
            row["distanceUnit"] = child.attrib.get("unit") or row.get("distanceUnit")
    return row


def min_text(a: str | None, b: str | None) -> str | None:
    if a is None:
        return b
    if b is None:
        return a
    return min(a, b)


def max_text(a: str | None, b: str | None) -> str | None:
    if a is None:
        return b
    if b is None:
        return a
    return max(a, b)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill a fresh Apple Health export.xml.")
    parser.add_argument("xml", type=Path)
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--batch-size", type=int, default=5000)
    args = parser.parse_args()
    print(json.dumps(backfill_xml(args.xml, args.db, args.batch_size), indent=2))


if __name__ == "__main__":
    main()
