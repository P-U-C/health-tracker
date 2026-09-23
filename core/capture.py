from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from core.schema import DEFAULT_DB, connect, load_schema
from ingest.hae_rest import parse_datetime, stable_id, to_float

VANCOUVER = ZoneInfo("America/Vancouver")
SUPPORTED_INTENTS = {"strength_set", "event", "manual_reading", "override", "symptom", "phase_decision", "meal"}
REST_WORDS = {"rest", "rested", "off", "skip", "skipped"}
PHOTO_MAX_BYTES = 6 * 1024 * 1024


class CaptureError(ValueError):
    pass


def log_mobile_capture(payload: dict[str, Any], db_path: str | Path = DEFAULT_DB, now: datetime | None = None) -> dict[str, Any]:
    intent = _normalize_intent(payload.get("intent"))
    if intent not in SUPPORTED_INTENTS:
        raise CaptureError(f"unsupported capture intent: {intent or 'missing'}")

    text = str(payload.get("text") or "").strip()
    fields = payload.get("fields") or {}
    if not isinstance(fields, dict):
        raise CaptureError("fields must be an object")
    if not text and not fields:
        raise CaptureError("capture requires text or fields")

    occurred_at = _capture_time(payload.get("occurred_at"), now)
    source = _clean_source(payload.get("source"))

    db_path = Path(db_path)
    conn = connect(db_path)
    try:
        load_schema(conn)
        if intent == "strength_set":
            result = _log_strength(conn, text, fields, occurred_at, source)
        elif intent == "meal":
            result = _log_meal(conn, text, fields, occurred_at, source, db_path)
        elif intent == "manual_reading":
            result = _log_reading(conn, text, fields, occurred_at, source)
        elif intent == "override":
            result = _log_override(conn, text, fields, occurred_at, source)
        else:
            result = _log_event(conn, intent, text, fields, occurred_at, source)
        _log_ingest(conn, intent, payload, result["records_written"], occurred_at)
        return result
    finally:
        conn.close()


def _log_strength(conn, text: str, fields: dict[str, Any], occurred_at: datetime, source: str) -> dict[str, Any]:
    parsed = _parse_strength(text, fields)
    if parsed.get("rest_day"):
        return _log_event(conn, "event", text or "Rest day", {"kind": "rest_day", **fields}, occurred_at, source)

    missing = [name for name in ("exercise", "sets", "reps") if parsed.get(name) in (None, "")]
    if missing:
        return _needs_review("strength_set", missing, "Need exercise plus sets x reps before logging strength.")

    exercise = str(parsed["exercise"]).strip()
    sets = int(parsed["sets"])
    reps = int(parsed["reps"])
    load_kg = to_float(parsed.get("load_kg"))
    rpe = to_float(parsed.get("rpe"))
    session_type = str(fields.get("session_type") or "strength")
    session_date = occurred_at.date()
    notes = text or fields.get("notes")
    ids: list[str] = []

    for set_no in range(1, max(sets, 1) + 1):
        e1rm = load_kg * (1 + reps / 30) if load_kg is not None and reps else None
        ids.append(stable_id("mobile", "strength_sets", session_date.isoformat(), exercise, set_no))
        conn.execute(
            """
            DELETE FROM strength_sets
            WHERE session_date = ? AND exercise = ? AND set_no = ?
            """,
            [session_date, exercise, set_no],
        )
        conn.execute(
            """
            INSERT INTO strength_sets (session_date, session_type, exercise, set_no, load_kg, reps, rpe, e1rm, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [session_date, session_type, exercise, set_no, load_kg, reps, rpe, e1rm, notes],
        )

    return {
        "ok": True,
        "intent": "strength_set",
        "stored_as": "strength_sets",
        "records_written": len(ids),
        "ids": ids,
        "needs_review": False,
        "summary": f"Logged {sets}x{reps} {exercise}" + (f" at {load_kg:g} kg" if load_kg is not None else ""),
    }


def _log_meal(conn, text: str, fields: dict[str, Any], occurred_at: datetime, source: str, db_path: Path) -> dict[str, Any]:
    parsed = _parse_meal(text, fields)
    photo_ref = _save_meal_photo(fields.get("photo_data_url") or fields.get("photo"), fields, occurred_at, source, db_path)
    description = str(fields.get("description") or _strip_prefix(text, "meal") or text or "").strip()
    if not description and photo_ref:
        description = "Photo meal capture"
    if not description and not photo_ref:
        return _needs_review("meal", ["description"], "Need meal text or a photo before logging nutrition.")

    macro_keys = ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g", "sodium_mg")
    has_macros = any(parsed.get(key) is not None for key in macro_keys)
    needs_review = not has_macros
    input_method = str(fields.get("input_method") or ("photo" if photo_ref else "text")).strip().lower()
    confidence = str(fields.get("confidence") or ("user_supplied" if has_macros else "pending")).strip()
    llm_status = str(fields.get("llm_status") or ("not_needed" if has_macros else "pending_estimate")).strip()
    meal_id = stable_id("mobile", "nutrition_logs", occurred_at.isoformat(), description, photo_ref or "", source)
    raw_json = json.dumps(
        {
            "text": text,
            "fields": {key: value for key, value in fields.items() if key not in {"photo", "photo_data_url"}},
            "parsed": parsed,
        },
        sort_keys=True,
        default=str,
    )

    conn.execute("DELETE FROM nutrition_logs WHERE meal_id = ?", [meal_id])
    conn.execute(
        """
        INSERT INTO nutrition_logs (
          meal_id, occurred_at, local_date, source, input_method, description, photo_ref,
          calories, protein_g, carbs_g, fat_g, fiber_g, sugar_g, sodium_mg,
          confidence, needs_review, llm_status, llm_model, raw_json, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            meal_id,
            occurred_at,
            occurred_at.date(),
            source,
            input_method,
            description,
            photo_ref,
            parsed.get("calories"),
            parsed.get("protein_g"),
            parsed.get("carbs_g"),
            parsed.get("fat_g"),
            parsed.get("fiber_g"),
            parsed.get("sugar_g"),
            parsed.get("sodium_mg"),
            confidence,
            needs_review,
            llm_status,
            fields.get("llm_model"),
            raw_json,
            fields.get("notes"),
        ],
    )
    return {
        "ok": True,
        "intent": "meal",
        "stored_as": "nutrition_logs",
        "records_written": 1,
        "ids": [meal_id],
        "needs_review": needs_review,
        "summary": _meal_summary(parsed, needs_review),
        "llm_status": llm_status,
        "photo_ref": photo_ref,
    }


def _log_reading(conn, text: str, fields: dict[str, Any], occurred_at: datetime, source: str) -> dict[str, Any]:
    parsed = _parse_reading(text, fields)
    missing = [name for name in ("metric", "value", "unit") if parsed.get(name) in (None, "")]
    if missing:
        return _needs_review("manual_reading", missing, "Need metric, value, and unit before logging a reading.")

    metric = str(parsed["metric"]).strip().lower().replace(" ", "_")
    value = to_float(parsed.get("value"))
    if value is None:
        return _needs_review("manual_reading", ["value"], "Reading value must be numeric.")
    unit = str(parsed["unit"]).strip()
    notes = text or fields.get("notes")
    reading_source = str(fields.get("source") or source or "ios")

    conn.execute(
        """
        DELETE FROM readings
        WHERE ts = ? AND source = ? AND metric = ?
        """,
        [occurred_at, reading_source, metric],
    )
    conn.execute(
        """
        INSERT INTO readings (ts, source, metric, value, unit, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [occurred_at, reading_source, metric, value, unit, notes],
    )
    reading_id = stable_id("mobile", "readings", occurred_at.isoformat(), reading_source, metric)
    return {
        "ok": True,
        "intent": "manual_reading",
        "stored_as": "readings",
        "records_written": 1,
        "ids": [reading_id],
        "needs_review": False,
        "summary": f"Logged {metric}: {value:g} {unit}",
    }


def _log_override(conn, text: str, fields: dict[str, Any], occurred_at: datetime, source: str) -> dict[str, Any]:
    decision = str(fields.get("decision") or _strip_prefix(text, "override") or text or "Override logged").strip()
    recommendation = str(fields.get("recommendation") or "current protocol recommendation").strip()
    reason = fields.get("reason") or text or None
    outcome = fields.get("outcome")
    phase_id = fields.get("phase_id")
    override_id = stable_id("mobile", "override", occurred_at.isoformat(), recommendation, decision, source)

    conn.execute("DELETE FROM overrides WHERE override_id = ?", [override_id])
    conn.execute(
        """
        INSERT INTO overrides (override_id, ts, recommendation, decision, reason, outcome, phase_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [override_id, occurred_at, recommendation, decision, reason, outcome, phase_id],
    )
    return {
        "ok": True,
        "intent": "override",
        "stored_as": "overrides",
        "records_written": 1,
        "ids": [override_id],
        "needs_review": False,
        "summary": f"Logged override: {decision}",
    }


def _log_event(conn, intent: str, text: str, fields: dict[str, Any], occurred_at: datetime, source: str) -> dict[str, Any]:
    kind = str(fields.get("kind") or _event_kind(intent, text)).strip()
    event_id = stable_id("mobile", "events", occurred_at.isoformat(), kind, text, source)
    conn.execute("DELETE FROM events WHERE event_id = ?", [event_id])
    conn.execute(
        """
        INSERT INTO events (event_id, kind, start_ts, end_ts, streams_tagged_out, hypothesis, prediction, outcome, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            event_id,
            kind,
            occurred_at,
            parse_datetime(fields.get("end_ts") or fields.get("end_at")),
            fields.get("streams_tagged_out"),
            fields.get("hypothesis"),
            fields.get("prediction"),
            fields.get("outcome"),
            text or fields.get("notes"),
        ],
    )
    return {
        "ok": True,
        "intent": intent,
        "stored_as": "events",
        "records_written": 1,
        "ids": [event_id],
        "needs_review": False,
        "summary": f"Logged {kind} event",
    }


def _parse_strength(text: str, fields: dict[str, Any]) -> dict[str, Any]:
    lower = text.lower()
    if fields.get("rest_day") is True or ("rest" in lower and not re.search(r"\d+\s*x\s*\d+", lower)):
        return {"rest_day": True}

    result: dict[str, Any] = {
        "exercise": fields.get("exercise"),
        "sets": fields.get("sets"),
        "reps": fields.get("reps"),
        "load_kg": fields.get("load_kg"),
        "rpe": fields.get("rpe"),
    }
    if result["sets"] in (None, "") or result["reps"] in (None, ""):
        if match := re.search(r"(?P<sets>\d+)\s*x\s*(?P<reps>\d+)", text, flags=re.IGNORECASE):
            result["sets"] = int(match.group("sets"))
            result["reps"] = int(match.group("reps"))
    if result["load_kg"] in (None, ""):
        if match := re.search(r"(?P<load>\d+(?:\.\d+)?)\s*kg\b", text, flags=re.IGNORECASE):
            result["load_kg"] = float(match.group("load"))
    if result["rpe"] in (None, ""):
        if match := re.search(r"\brpe\s*(?P<rpe>\d+(?:\.\d+)?)\b", text, flags=re.IGNORECASE):
            result["rpe"] = float(match.group("rpe"))
    if not result["exercise"] and text:
        result["exercise"] = _guess_exercise(text)
    return result


def _parse_reading(text: str, fields: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"metric": fields.get("metric"), "value": fields.get("value"), "unit": fields.get("unit")}
    if all(result.values()) or not text:
        return result
    match = re.search(r"(?P<metric>[a-zA-Z_ ]+?)\s+(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z/%]+)\b", text)
    if match:
        result.update(match.groupdict())
    return result


def _parse_meal(text: str, fields: dict[str, Any]) -> dict[str, Any]:
    return {
        "calories": _macro_value(text, fields, ("calories", "kcal"), r"(?:kcal|calories|cals?|cal)\b"),
        "protein_g": _macro_value(text, fields, ("protein_g", "protein"), r"(?:protein|prot)\b", shorthand="p"),
        "carbs_g": _macro_value(text, fields, ("carbs_g", "carbs", "carbohydrates"), r"(?:carbs?|carbohydrates?)\b", shorthand="c"),
        "fat_g": _macro_value(text, fields, ("fat_g", "fat"), r"\bfat\b", shorthand="f"),
        "fiber_g": _macro_value(text, fields, ("fiber_g", "fiber", "fibre"), r"(?:fiber|fibre)\b"),
        "sugar_g": _macro_value(text, fields, ("sugar_g", "sugar"), r"\bsugar\b"),
        "sodium_mg": _macro_value(text, fields, ("sodium_mg", "sodium"), r"\bsodium\b", unit="mg"),
    }


def _macro_value(text: str, fields: dict[str, Any], field_names: tuple[str, ...], label_pattern: str, shorthand: str | None = None, unit: str = "g") -> float | None:
    for name in field_names:
        value = to_float(fields.get(name))
        if value is not None:
            return value
    if not text:
        return None
    number = r"(?P<value>-?\d+(?:\.\d+)?)"
    patterns = [
        rf"{label_pattern}\s*[:=]?\s*{number}\s*{unit}?",
        rf"{number}\s*{unit}\s*{label_pattern}",
    ]
    if unit == "mg":
        patterns.insert(0, rf"{number}\s*mg\s*{label_pattern}")
    elif label_pattern.startswith("(?:kcal"):
        patterns = [rf"{number}\s*(?:kcal|calories|cals?|cal)\b", rf"(?:kcal|calories|cals?|cal)\s*[:=]?\s*{number}"]
    if shorthand:
        patterns.append(rf"\b{number}\s*{re.escape(shorthand)}\b")
    for pattern in patterns:
        if match := re.search(pattern, text, flags=re.IGNORECASE):
            return float(match.group("value"))
    return None


def _save_meal_photo(data_url: Any, fields: dict[str, Any], occurred_at: datetime, source: str, db_path: Path) -> str | None:
    if not data_url:
        return None
    payload = str(data_url)
    match = re.match(r"^data:(?P<mime>image/(?:jpeg|jpg|png|webp));base64,(?P<data>.+)$", payload, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        raise CaptureError("meal photo must be a data URL image")
    try:
        raw = base64.b64decode(match.group("data"), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise CaptureError("meal photo is not valid base64") from exc
    if len(raw) > PHOTO_MAX_BYTES:
        raise CaptureError("meal photo is too large")
    mime = match.group("mime").lower()
    ext = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png", "image/webp": "webp"}[mime]
    digest = hashlib.sha256(raw).hexdigest()
    safe_source = _clean_source(source)
    root = Path(os.getenv("HEALTH_NUTRITION_PHOTO_DIR") or (db_path.parent / "imports" / "nutrition" / "photos"))
    root.mkdir(parents=True, exist_ok=True)
    filename = f"{occurred_at.date().isoformat()}_{safe_source}_{digest[:20]}.{ext}"
    target = root / filename
    target.write_bytes(raw)
    try:
        return str(target.relative_to(db_path.parent))
    except ValueError:
        return str(target)


def _meal_summary(parsed: dict[str, Any], needs_review: bool) -> str:
    if needs_review:
        return "Saved meal for macro estimate"
    parts = []
    if parsed.get("calories") is not None:
        parts.append(f"{parsed['calories']:g} kcal")
    if parsed.get("protein_g") is not None:
        parts.append(f"{parsed['protein_g']:g} g protein")
    if parsed.get("carbs_g") is not None:
        parts.append(f"{parsed['carbs_g']:g} g carbs")
    if parsed.get("fat_g") is not None:
        parts.append(f"{parsed['fat_g']:g} g fat")
    return "Logged meal: " + ", ".join(parts or ["macros"])


def _guess_exercise(text: str) -> str:
    cleaned = re.sub(r"\brpe\s*\d+(?:\.\d+)?\b", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\d+\s*x\s*\d+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\d+(?:\.\d+)?\s*kg\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(logged|log|did|done)\s+", "", cleaned.strip(), flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip(" .,:;-_") or "strength"


def _event_kind(intent: str, text: str) -> str:
    words = set(re.findall(r"[a-z]+", text.lower()))
    if words & REST_WORDS:
        return "rest_day"
    if intent == "symptom":
        return "symptom"
    if intent == "phase_decision":
        return "phase_decision"
    if "fast" in words or "fasted" in words:
        return "fast"
    if "travel" in words:
        return "travel"
    if "alcohol" in words:
        return "alcohol"
    return "event"


def _capture_time(value: Any, now: datetime | None) -> datetime:
    parsed = parse_datetime(value)
    if parsed is not None:
        return parsed
    if now is None:
        return datetime.now(VANCOUVER).replace(tzinfo=None, microsecond=0)
    if now.tzinfo is not None:
        now = now.astimezone(VANCOUVER).replace(tzinfo=None)
    return now.replace(microsecond=0)


def _clean_source(value: Any) -> str:
    source = str(value or "ios").strip().lower()
    source = re.sub(r"[^a-z0-9_.:-]+", "-", source)
    return source[:40] or "ios"


def _normalize_intent(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _strip_prefix(text: str, prefix: str) -> str:
    return re.sub(rf"^\s*{re.escape(prefix)}\s*:?\s*", "", text, flags=re.IGNORECASE)


def _needs_review(intent: str, missing: list[str], message: str) -> dict[str, Any]:
    return {
        "ok": False,
        "intent": intent,
        "stored_as": None,
        "records_written": 0,
        "ids": [],
        "needs_review": True,
        "missing_fields": missing,
        "summary": message,
    }


def _log_ingest(conn, intent: str, payload: dict[str, Any], records_written: int, occurred_at: datetime) -> None:
    if records_written <= 0:
        return
    conn.execute(
        """
        INSERT INTO ingest_log (received_at, source, payload_hash, rows_upserted, min_ts, max_ts)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            datetime.now(timezone.utc).replace(tzinfo=None),
            f"mobile_capture:{intent}",
            hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest(),
            records_written,
            occurred_at,
            occurred_at,
        ],
    )
