from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
VANCOUVER = ZoneInfo("America/Vancouver")
MPH_TO_KMH = 1.609344
INCH_TO_CM = 2.54


@dataclass(frozen=True)
class CsvContract:
    name: str
    source_rel: str
    table: str
    export_rel: str
    export_columns: tuple[str, ...]
    db_columns: tuple[str, ...]
    format_kinds: dict[str, str]
    order_by: tuple[str, ...]
    line_terminator: str
    key_columns: tuple[str, ...]


APPLE_CRLF = "\r\n"
DEXA_LF = "\n"

APPLE_CONTRACTS: tuple[CsvContract, ...] = (
    CsvContract(
        name="activity_rings",
        source_rel="data/apple_health/activity_rings.csv",
        table="activity_rings",
        export_rel="apple_health/activity_rings.csv",
        export_columns=("date", "active_cal", "active_goal", "exercise_min", "exercise_goal", "stand_hrs", "stand_goal"),
        db_columns=("date", "active_cal", "active_goal", "exercise_min", "exercise_goal", "stand_hrs", "stand_goal"),
        format_kinds={"date": "date", "active_cal": "int", "active_goal": "int", "exercise_min": "int", "exercise_goal": "int", "stand_hrs": "int", "stand_goal": "int"},
        order_by=("import_id",),
        line_terminator=APPLE_CRLF,
        key_columns=("import_id",),
    ),
    CsvContract(
        name="body_composition",
        source_rel="data/apple_health/body_composition.csv",
        table="body_comp_samples",
        export_rel="apple_health/body_composition.csv",
        export_columns=("date", "type", "value", "source"),
        db_columns=("date", "type", "value", "source"),
        format_kinds={"date": "date", "type": "text", "value": "float", "source": "text"},
        order_by=("import_id",),
        line_terminator=APPLE_CRLF,
        key_columns=("import_id",),
    ),
    CsvContract(
        name="daily_metrics",
        source_rel="data/apple_health/daily_metrics.csv",
        table="daily_metrics",
        export_rel="apple_health/daily_metrics.csv",
        export_columns=(
            "date", "active_cal", "asymmetry_pct", "basal_cal", "daylight_min", "distance_km",
            "double_support_pct", "env_audio_db", "exercise_min", "flights", "headphone_db",
            "physical_effort", "resp_rate", "run_gct_ms", "run_power_w", "run_speed_kmh",
            "run_stride_cm", "run_vert_osc_cm", "stair_down_speed", "stair_up_speed",
            "stand_min", "steps", "walk_speed_kmh", "walk_stride_cm",
        ),
        db_columns=(
            "date", "active_cal", "asymmetry_pct", "basal_cal", "daylight_min", "distance_km",
            "double_support_pct", "env_audio_db", "exercise_min", "flights", "headphone_db",
            "physical_effort", "resp_rate", "run_gct_ms", "run_power_w", "run_speed_kmh",
            "run_stride_cm", "run_vert_osc_cm", "stair_down_speed", "stair_up_speed",
            "stand_min", "steps", "walk_speed_kmh", "walk_stride_cm",
        ),
        format_kinds={c: ("date" if c == "date" else "float") for c in (
            "date", "active_cal", "asymmetry_pct", "basal_cal", "daylight_min", "distance_km",
            "double_support_pct", "env_audio_db", "exercise_min", "flights", "headphone_db",
            "physical_effort", "resp_rate", "run_gct_ms", "run_power_w", "run_speed_kmh",
            "run_stride_cm", "run_vert_osc_cm", "stair_down_speed", "stair_up_speed",
            "stand_min", "steps", "walk_speed_kmh", "walk_stride_cm",
        )},
        order_by=("import_id",),
        line_terminator=APPLE_CRLF,
        key_columns=("import_id",),
    ),
    CsvContract(
        name="heart_rate_hourly",
        source_rel="data/apple_health/heart_rate_hourly.csv",
        table="hr_hourly",
        export_rel="apple_health/heart_rate_hourly.csv",
        export_columns=("datetime", "hr_avg", "hr_min", "hr_max", "samples"),
        db_columns=("hour", "hr_avg", "hr_min", "hr_max", "samples"),
        format_kinds={"datetime": "datetime_hour", "hr_avg": "int", "hr_min": "int", "hr_max": "int", "samples": "int"},
        order_by=("import_id",),
        line_terminator=APPLE_CRLF,
        key_columns=("import_id",),
    ),
    CsvContract(
        name="hrv",
        source_rel="data/apple_health/hrv.csv",
        table="hrv_samples",
        export_rel="apple_health/hrv.csv",
        export_columns=("date", "hrv_ms"),
        db_columns=("ts", "hrv_ms"),
        format_kinds={"date": "datetime_minute", "hrv_ms": "float"},
        order_by=("import_id",),
        line_terminator=APPLE_CRLF,
        key_columns=("import_id",),
    ),
    CsvContract(
        name="nutrition_daily",
        source_rel="data/apple_health/nutrition_daily.csv",
        table="nutrition_daily",
        export_rel="apple_health/nutrition_daily.csv",
        export_columns=(
            "date", "calcium_mg", "calories", "carbs_g", "cholesterol_mg", "fat_g",
            "fiber_g", "iron_mg", "mono_fat_g", "poly_fat_g", "potassium_mg",
            "protein_g", "sat_fat_g", "sodium_mg", "sugar_g", "vitamin_c_mg",
        ),
        db_columns=(
            "date", "calcium_mg", "calories", "carbs_g", "cholesterol_mg", "fat_g",
            "fiber_g", "iron_mg", "mono_fat_g", "poly_fat_g", "potassium_mg",
            "protein_g", "sat_fat_g", "sodium_mg", "sugar_g", "vitamin_c_mg",
        ),
        format_kinds={c: ("date" if c == "date" else "float") for c in (
            "date", "calcium_mg", "calories", "carbs_g", "cholesterol_mg", "fat_g",
            "fiber_g", "iron_mg", "mono_fat_g", "poly_fat_g", "potassium_mg",
            "protein_g", "sat_fat_g", "sodium_mg", "sugar_g", "vitamin_c_mg",
        )},
        order_by=("import_id",),
        line_terminator=APPLE_CRLF,
        key_columns=("import_id",),
    ),
    CsvContract(
        name="oxygen_saturation",
        source_rel="data/apple_health/oxygen_saturation.csv",
        table="spo2_samples",
        export_rel="apple_health/oxygen_saturation.csv",
        export_columns=("date", "spo2_pct"),
        db_columns=("ts", "spo2_pct"),
        format_kinds={"date": "datetime_minute", "spo2_pct": "float"},
        order_by=("import_id",),
        line_terminator=APPLE_CRLF,
        key_columns=("import_id",),
    ),
    CsvContract(
        name="resting_hr",
        source_rel="data/apple_health/resting_hr.csv",
        table="resting_hr",
        export_rel="apple_health/resting_hr.csv",
        export_columns=("date", "resting_hr"),
        db_columns=("date", "resting_hr"),
        format_kinds={"date": "date", "resting_hr": "int"},
        order_by=("import_id",),
        line_terminator=APPLE_CRLF,
        key_columns=("import_id",),
    ),
    CsvContract(
        name="sleep",
        source_rel="data/apple_health/sleep.csv",
        table="sleep_segments",
        export_rel="apple_health/sleep.csv",
        export_columns=("start", "end", "value", "source"),
        db_columns=("start_ts", "end_ts", "value", "source"),
        format_kinds={"start": "datetime_minute", "end": "datetime_minute", "value": "text", "source": "text"},
        order_by=("import_id",),
        line_terminator=APPLE_CRLF,
        key_columns=("import_id",),
    ),
    CsvContract(
        name="vo2max",
        source_rel="data/apple_health/vo2max.csv",
        table="vo2max",
        export_rel="apple_health/vo2max.csv",
        export_columns=("date", "vo2max"),
        db_columns=("date", "vo2max"),
        format_kinds={"date": "date", "vo2max": "float"},
        order_by=("import_id",),
        line_terminator=APPLE_CRLF,
        key_columns=("import_id",),
    ),
    CsvContract(
        name="workouts",
        source_rel="data/apple_health/workouts.csv",
        table="workouts",
        export_rel="apple_health/workouts.csv",
        export_columns=("date", "type", "duration_min", "distance_km", "calories", "hr_avg", "hr_min", "hr_max", "source"),
        db_columns=("start_ts", "type", "duration_min", "distance_km", "calories", "hr_avg", "hr_min", "hr_max", "source"),
        format_kinds={"date": "datetime_minute", "type": "text", "duration_min": "float", "distance_km": "float", "calories": "int", "hr_avg": "int", "hr_min": "int", "hr_max": "int", "source": "text"},
        order_by=("import_id",),
        line_terminator=APPLE_CRLF,
        key_columns=("import_id",),
    ),
)

DEXA_CONTRACTS: tuple[CsvContract, ...] = (
    CsvContract(
        name="dexa_regional",
        source_rel="data/dexa/dexa_regional.csv",
        table="dexa_regional",
        export_rel="dexa/dexa_regional.csv",
        export_columns=("scan_date", "region", "fat_kg", "lean_bmc_kg", "total_kg", "pct_fat", "yn_pctile", "am_pctile"),
        db_columns=("scan_date", "region", "fat_kg", "lean_bmc_kg", "total_kg", "pct_fat", "yn_pctile", "am_pctile"),
        format_kinds={"scan_date": "date", "region": "text", "fat_kg": "float", "lean_bmc_kg": "float", "total_kg": "float", "pct_fat": "float", "yn_pctile": "int", "am_pctile": "int"},
        order_by=("import_id",),
        line_terminator=DEXA_LF,
        key_columns=("scan_date", "region"),
    ),
    CsvContract(
        name="dexa_scans",
        source_rel="data/dexa/dexa_scans.csv",
        table="dexa_scans",
        export_rel="dexa/dexa_scans.csv",
        export_columns=(
            "scan_number", "scan_date", "scan_id", "weight_kg", "fat_mass_kg", "lean_bmc_kg",
            "body_fat_pct", "bf_yn_pctile", "bf_am_pctile", "almi_kg_m2", "almi_yn_pctile",
            "almi_am_pctile", "lmi_kg_m2", "lmi_yn_pctile", "lmi_am_pctile", "fmi_kg_m2",
            "fmi_yn_pctile", "fmi_am_pctile", "vat_mass_g", "vat_volume_cm3", "vat_area_cm2",
            "appendicular_lean_bmc_kg", "subtotal_fat_kg", "subtotal_lean_bmc_kg",
            "subtotal_pct_fat", "trunk_fat_kg", "trunk_pct_fat", "android_pct_fat",
            "gynoid_pct_fat", "android_gynoid_ratio", "pct_fat_trunk_legs_ratio",
            "trunk_limb_fat_mass_ratio", "l_arm_lean_bmc_kg", "r_arm_lean_bmc_kg",
            "l_leg_lean_bmc_kg", "r_leg_lean_bmc_kg", "leg_lean_asymmetry_pct",
            "bmd_total_g_cm2", "bmd_t_score", "bmd_z_score", "provider", "reported_by",
            "source_file",
        ),
        db_columns=(
            "scan_number", "scan_date", "scan_id", "weight_kg", "fat_mass_kg", "lean_bmc_kg",
            "body_fat_pct", "bf_yn_pctile", "bf_am_pctile", "almi_kg_m2", "almi_yn_pctile",
            "almi_am_pctile", "lmi_kg_m2", "lmi_yn_pctile", "lmi_am_pctile", "fmi_kg_m2",
            "fmi_yn_pctile", "fmi_am_pctile", "vat_mass_g", "vat_volume_cm3", "vat_area_cm2",
            "appendicular_lean_bmc_kg", "subtotal_fat_kg", "subtotal_lean_bmc_kg",
            "subtotal_pct_fat", "trunk_fat_kg", "trunk_pct_fat", "android_pct_fat",
            "gynoid_pct_fat", "android_gynoid_ratio", "pct_fat_trunk_legs_ratio",
            "trunk_limb_fat_mass_ratio", "l_arm_lean_bmc_kg", "r_arm_lean_bmc_kg",
            "l_leg_lean_bmc_kg", "r_leg_lean_bmc_kg", "leg_lean_asymmetry_pct",
            "bmd_total_g_cm2", "bmd_t_score", "bmd_z_score", "provider", "reported_by",
            "source_file",
        ),
        format_kinds={
            **{c: "float" for c in (
                "weight_kg", "fat_mass_kg", "lean_bmc_kg", "body_fat_pct", "almi_kg_m2",
                "lmi_kg_m2", "fmi_kg_m2", "vat_mass_g", "vat_volume_cm3", "vat_area_cm2",
                "appendicular_lean_bmc_kg", "subtotal_fat_kg", "subtotal_lean_bmc_kg",
                "subtotal_pct_fat", "trunk_fat_kg", "trunk_pct_fat", "android_pct_fat",
                "gynoid_pct_fat", "android_gynoid_ratio", "pct_fat_trunk_legs_ratio",
                "trunk_limb_fat_mass_ratio", "l_arm_lean_bmc_kg", "r_arm_lean_bmc_kg",
                "l_leg_lean_bmc_kg", "r_leg_lean_bmc_kg", "leg_lean_asymmetry_pct",
                "bmd_total_g_cm2", "bmd_t_score", "bmd_z_score",
            )},
            **{c: "int" for c in (
                "scan_number", "bf_yn_pctile", "bf_am_pctile", "almi_yn_pctile",
                "almi_am_pctile", "lmi_yn_pctile", "lmi_am_pctile", "fmi_yn_pctile",
                "fmi_am_pctile",
            )},
            "scan_date": "date",
            "scan_id": "text",
            "provider": "text",
            "reported_by": "text",
            "source_file": "text",
        },
        order_by=("scan_date",),
        line_terminator=DEXA_LF,
        key_columns=("scan_date",),
    ),
)

ALL_CONTRACTS: tuple[CsvContract, ...] = APPLE_CONTRACTS + DEXA_CONTRACTS
TABLE_BY_PATH = {contract.source_rel: contract.table for contract in ALL_CONTRACTS}


def load_source_dataframe(contract: CsvContract, root: Path = REPO_ROOT) -> pd.DataFrame:
    source = root / contract.source_rel
    df = pd.read_csv(source, dtype=str, keep_default_na=False)
    df.insert(0, "import_id", [f"{contract.source_rel}:{idx:08d}" for idx in range(len(df))])

    if contract.name == "heart_rate_hourly":
        df = df.rename(columns={"datetime": "hour"})
        df["hour"] = df["hour"].map(lambda value: normalize_timestamp(value, "hour"))
    elif contract.name in {"hrv", "oxygen_saturation"}:
        df = df.rename(columns={"date": "ts"})
        df["ts"] = df["ts"].map(lambda value: normalize_timestamp(value, "minute"))
        if contract.name == "hrv":
            df["source"] = "apple_watch"
    elif contract.name == "sleep":
        df = df.rename(columns={"start": "start_ts", "end": "end_ts"})
        df["start_ts"] = df["start_ts"].map(lambda value: normalize_timestamp(value, "minute"))
        df["end_ts"] = df["end_ts"].map(lambda value: normalize_timestamp(value, "minute"))
    elif contract.name == "workouts":
        df = df.rename(columns={"date": "start_ts"})
        df["start_ts"] = df["start_ts"].map(lambda value: normalize_timestamp(value, "minute"))
        df["workout_id"] = [f"package-workout-{idx:08d}" for idx in range(len(df))]
        df["trimp"] = pd.NA
        df["srpe_load"] = pd.NA
        df["session_rpe"] = pd.NA
    elif contract.name == "body_composition":
        values = pd.to_numeric(df["value"], errors="coerce")
        mask = (df["type"] == "body_fat_pct") & values.notna() & (values < 1)
        values.loc[mask] = values.loc[mask] * 100
        df["value"] = values
    elif contract.name == "daily_metrics":
        for column, factor in {
            "walk_speed_kmh": MPH_TO_KMH,
            "run_speed_kmh": MPH_TO_KMH,
            "walk_stride_cm": INCH_TO_CM,
        }.items():
            values = pd.to_numeric(df[column], errors="coerce")
            df[column] = values * factor
    elif contract.name == "dexa_scans":
        df = df.drop(columns=["import_id"])
        df["conditions_json"] = ""
    elif contract.name == "dexa_regional":
        pass
    elif contract.name == "nutrition_daily":
        df["notes"] = ""

    return coerce_contract_types(df, contract)


def coerce_contract_types(df: pd.DataFrame, contract: CsvContract) -> pd.DataFrame:
    df = df.copy()
    export_to_db = dict(zip(contract.export_columns, contract.db_columns))
    for export_col, kind in contract.format_kinds.items():
        db_col = export_to_db[export_col]
        if db_col not in df.columns:
            continue
        if kind == "int":
            df[db_col] = pd.to_numeric(df[db_col], errors="coerce").astype("Int64")
        elif kind == "float":
            df[db_col] = pd.to_numeric(df[db_col], errors="coerce")
    return df


def normalize_timestamp(value: str, granularity: str) -> str:
    if not value:
        return value
    fmt = "%Y-%m-%d %H" if granularity == "hour" else "%Y-%m-%d %H:%M"
    dt = datetime.strptime(value, fmt)
    if dt.replace(tzinfo=VANCOUVER).dst() != timedelta(0):
        dt = dt + timedelta(hours=1)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def project_export_frame(df: pd.DataFrame, contract: CsvContract) -> pd.DataFrame:
    projected = pd.DataFrame()
    for export_col, db_col in zip(contract.export_columns, contract.db_columns):
        projected[export_col] = df[db_col]
    return projected


def insert_columns(contract: CsvContract) -> tuple[str, ...]:
    if contract.name == "dexa_scans":
        return contract.db_columns + ("conditions_json",)
    if contract.name == "dexa_regional":
        return ("import_id",) + contract.db_columns
    if contract.name == "nutrition_daily":
        return ("import_id",) + contract.db_columns + ("notes",)
    if contract.name == "workouts":
        return ("import_id", "workout_id") + contract.db_columns + ("trimp", "srpe_load", "session_rpe")
    if "import_id" in loadless_hidden_columns(contract):
        return ("import_id",) + contract.db_columns
    return contract.db_columns


def loadless_hidden_columns(contract: CsvContract) -> tuple[str, ...]:
    return () if contract.name.startswith("dexa_") else ("import_id",)
