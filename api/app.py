from __future__ import annotations

import hashlib
import hmac
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from secrets import compare_digest
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from api.dashboard_view import render_dashboard
from api.mobile_app_view import render_icon_svg, render_manifest, render_mobile_app, render_service_worker
from core.capture import CaptureError, log_mobile_capture
from core.dashboard import build_dashboard_model
from core.mobile import build_context_packet, build_today_model
from core.schema import DEFAULT_DB, connect, load_schema, table_count
from ingest.hae_rest import ingest_hae_payload

dashboard_security = HTTPBasic(auto_error=False)
MOBILE_SESSION_COOKIE = "health_mobile_session"
MOBILE_SESSION_TTL_SECONDS = 60 * 60 * 24 * 30


def db_path() -> Path:
    return Path(os.getenv("HEALTH_DB", str(DEFAULT_DB)))


def require_ingest_auth(authorization: str | None) -> None:
    token = os.getenv("HEALTH_INGEST_TOKEN")
    if not token:
        if os.getenv("HEALTH_ALLOW_DEV_AUTH") == "1":
            return
        raise HTTPException(status_code=503, detail="HEALTH_INGEST_TOKEN is not configured")
    if authorization != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="invalid bearer token")


def require_app_auth(authorization: str | None, request: Request | None = None) -> None:
    if os.getenv("HEALTH_ALLOW_DEV_AUTH") == "1":
        return
    if authorization and authorization.startswith("Bearer ") and _valid_app_token(authorization[len("Bearer "):]):
        return
    if request is not None and _valid_mobile_session(request.cookies.get(MOBILE_SESSION_COOKIE)):
        return
    raise HTTPException(status_code=401, detail="app auth required")


def _valid_app_token(candidate: str | None) -> bool:
    token = os.getenv("HEALTH_APP_TOKEN") or os.getenv("HEALTH_INGEST_TOKEN")
    return bool(token and candidate and compare_digest(candidate.encode("utf-8"), token.encode("utf-8")))


def _valid_dashboard_login(username: str | None, password: str | None) -> bool:
    expected_password = os.getenv("HEALTH_DASHBOARD_PASSWORD")
    expected_user = os.getenv("HEALTH_DASHBOARD_USER", "chad")
    if not expected_password or not username or not password:
        return False
    user_ok = compare_digest(username.encode("utf-8"), expected_user.encode("utf-8"))
    password_ok = compare_digest(password.encode("utf-8"), expected_password.encode("utf-8"))
    return user_ok and password_ok


def _mobile_session_secret() -> bytes:
    material = os.getenv("HEALTH_APP_SESSION_SECRET") or os.getenv("HEALTH_APP_TOKEN") or os.getenv("HEALTH_INGEST_TOKEN") or os.getenv("HEALTH_DASHBOARD_PASSWORD")
    if not material:
        raise HTTPException(status_code=503, detail="mobile session secret is not configured")
    return material.encode("utf-8")


def _make_mobile_session(username: str) -> str:
    expires = int(time.time()) + MOBILE_SESSION_TTL_SECONDS
    payload = f"{username}:{expires}"
    signature = hmac.new(_mobile_session_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{signature}"


def _valid_mobile_session(cookie: str | None) -> bool:
    if not cookie:
        return False
    try:
        username, expires_text, signature = cookie.split(":", 2)
        expires = int(expires_text)
    except ValueError:
        return False
    if expires < int(time.time()):
        return False
    payload = f"{username}:{expires}"
    expected = hmac.new(_mobile_session_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return compare_digest(signature.encode("utf-8"), expected.encode("utf-8"))


def require_dashboard_auth(credentials: HTTPBasicCredentials | None = Depends(dashboard_security)) -> None:
    password = os.getenv("HEALTH_DASHBOARD_PASSWORD")
    username = os.getenv("HEALTH_DASHBOARD_USER", "chad")
    if not password:
        if os.getenv("HEALTH_ALLOW_DEV_AUTH") == "1":
            return
        raise HTTPException(status_code=503, detail="HEALTH_DASHBOARD_PASSWORD is not configured")
    if credentials is None:
        raise _dashboard_unauthorized()
    username_ok = compare_digest(credentials.username.encode("utf-8"), username.encode("utf-8"))
    password_ok = compare_digest(credentials.password.encode("utf-8"), password.encode("utf-8"))
    if not (username_ok and password_ok):
        raise _dashboard_unauthorized()


def _dashboard_unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="dashboard auth required",
        headers={"WWW-Authenticate": 'Basic realm="health-dashboard"'},
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    conn = connect(db_path())
    try:
        load_schema(conn)
    finally:
        conn.close()
    yield


app = FastAPI(title="Personal Health System", version="0.1.0", lifespan=lifespan)



@app.get("/app", response_class=HTMLResponse, include_in_schema=False)
def mobile_app() -> HTMLResponse:
    return HTMLResponse(render_mobile_app())


@app.get("/app/manifest.webmanifest", include_in_schema=False)
def mobile_manifest() -> Response:
    return Response(render_manifest(), media_type="application/manifest+json")


@app.get("/app/service-worker.js", include_in_schema=False)
def mobile_service_worker() -> Response:
    return Response(render_service_worker(), media_type="text/javascript")


@app.get("/app/icon.svg", include_in_schema=False)
def mobile_icon() -> Response:
    return Response(render_icon_svg(), media_type="image/svg+xml")


@app.get("/api/mobile/session", operation_id="get_mobile_session")
def mobile_session_status(request: Request) -> dict[str, Any]:
    return {"authenticated": _valid_mobile_session(request.cookies.get(MOBILE_SESSION_COOKIE))}


@app.post("/api/mobile/session", operation_id="post_mobile_session")
async def mobile_session(request: Request) -> JSONResponse:
    payload = await request.json()
    username = str(payload.get("username") or "chad")
    password = str(payload.get("password") or "")
    token = str(payload.get("token") or "")
    if not (_valid_app_token(token) or _valid_dashboard_login(username, password)):
        raise HTTPException(status_code=401, detail="invalid mobile credentials")
    response = JSONResponse({"ok": True, "authenticated": True})
    response.set_cookie(
        MOBILE_SESSION_COOKIE,
        _make_mobile_session(username),
        max_age=MOBILE_SESSION_TTL_SECONDS,
        secure=True,
        httponly=True,
        samesite="lax",
    )
    return response


@app.delete("/api/mobile/session", operation_id="delete_mobile_session")
def mobile_session_logout() -> JSONResponse:
    response = JSONResponse({"ok": True, "authenticated": False})
    response.delete_cookie(MOBILE_SESSION_COOKIE)
    return response


@app.get("/status", operation_id="get_status")
def status() -> dict[str, Any]:
    conn = connect(db_path())
    try:
        load_schema(conn)
        dexa_rows = table_count(conn, "dexa_scans")
        latest_ingest = conn.execute("SELECT MAX(received_at) FROM ingest_log").fetchone()[0]
        latest_dexa = conn.execute("SELECT MAX(scan_date) FROM dexa_scans").fetchone()[0]
        latest_weight = conn.execute("SELECT MAX(date) FROM body_comp_samples WHERE type = 'weight_kg'").fetchone()[0]
        return {
            "ok": True,
            "phase": None,
            "dexa_scans": {"rows": dexa_rows, "latest": str(latest_dexa) if latest_dexa else None},
            "body_weight": {"latest": str(latest_weight) if latest_weight else None},
            "latest_ingest": str(latest_ingest) if latest_ingest else None,
        }
    finally:
        conn.close()


@app.get("/api/dashboard/overview", operation_id="get_dashboard_overview")
def dashboard_overview(_: None = Depends(require_dashboard_auth)) -> dict[str, Any]:
    return build_dashboard_model(db_path())


@app.get("/api/mobile/today", operation_id="get_mobile_today")
def mobile_today() -> dict[str, Any]:
    return build_today_model(db_path())


@app.get("/api/mobile/context", operation_id="get_mobile_context")
def mobile_context() -> dict[str, Any]:
    return {"format": "markdown", "markdown": build_context_packet(db_path())}


@app.post("/api/mobile/capture", operation_id="post_mobile_capture")
async def mobile_capture(request: Request, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_app_auth(authorization, request)
    payload = await request.json()
    try:
        return log_mobile_capture(payload, db_path())
    except CaptureError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/mobile/links", operation_id="get_mobile_links")
def mobile_links(request: Request, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_app_auth(authorization, request)
    return {
        "claude_project_url": os.getenv("HEALTH_CLAUDE_PROJECT_URL"),
        "chatgpt_project_url": os.getenv("HEALTH_CHATGPT_PROJECT_URL"),
        "context_packet": "/api/mobile/context",
        "share_text": "Use the current Health Context Packet as the source of truth for this protocol check-in.",
    }


@app.get("/dashboard", response_class=HTMLResponse, operation_id="get_dashboard")
def dashboard(_: None = Depends(require_dashboard_auth)) -> HTMLResponse:
    return HTMLResponse(render_dashboard(build_dashboard_model(db_path())))


@app.post("/ingest/hae", operation_id="ingest_hae")
async def ingest_hae(request: Request, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_ingest_auth(authorization)
    payload = await request.json()
    return ingest_hae_payload(payload, db_path())
