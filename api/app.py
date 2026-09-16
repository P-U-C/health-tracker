from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from secrets import compare_digest
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from api.dashboard_view import render_dashboard
from core.dashboard import build_dashboard_model
from core.schema import DEFAULT_DB, connect, load_schema, table_count
from ingest.hae_rest import ingest_hae_payload

dashboard_security = HTTPBasic(auto_error=False)


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


@app.get("/dashboard", response_class=HTMLResponse, operation_id="get_dashboard")
def dashboard(_: None = Depends(require_dashboard_auth)) -> HTMLResponse:
    return HTMLResponse(render_dashboard(build_dashboard_model(db_path())))


@app.post("/ingest/hae", operation_id="ingest_hae")
async def ingest_hae(request: Request, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    require_ingest_auth(authorization)
    payload = await request.json()
    return ingest_hae_payload(payload, db_path())
