# -*- coding: utf-8 -*-
"""FastAPI application entry point."""

from __future__ import annotations

import logging
import os
import sys

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from tuvi_mcp.api.auth import UnauthorizedError, auth_status_for_startup, probe_jwks_key_count
from tuvi_mcp.api.routes import auspicious, calendar, health, horoscope

logger = logging.getLogger(__name__)

app = FastAPI(title="TuViMCP REST")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def validate_auth_configuration() -> None:
    """Fail fast in production without SUPABASE_URL; warn when JWKS or auth bypass is misconfigured."""
    status = auth_status_for_startup()
    for warning in status.warnings:
        logger.warning(warning)

    if status.fatal_error:
        logger.error(status.fatal_error)
        sys.exit(1)

    if status.auth_enabled:
        key_count = probe_jwks_key_count()
        if key_count == 0:
            logger.warning(
                "JWKS probe returned 0 keys for %s — JWT verification will fail until "
                "Supabase JWT signing keys are migrated to ES256.",
                status.supabase_url,
            )
        else:
            logger.info("JWKS probe OK: %d signing key(s) for %s", key_count, status.supabase_url)
    else:
        logger.warning(
            "JWT auth is DISABLED (TUVI_MCP_AUTH_DISABLED). POST /v1/horoscope/* accepts "
            "requests without Bearer tokens — dev/pytest only."
        )


@app.exception_handler(UnauthorizedError)
async def unauthorized_exception_handler(_request: Request, exc: UnauthorizedError) -> JSONResponse:
    """Handle JWT auth failures with unwrapped 401 responses."""
    return JSONResponse(
        status_code=401,
        headers={"WWW-Authenticate": "Bearer"},
        content={
            "error": {
                "code": "UNAUTHORIZED",
                "detail": exc.detail,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Map Pydantic validation failures to D-06 error shape."""
    locs = [str(part) for err in exc.errors() for part in err.get("loc", [])]
    loc_text = " ".join(locs).lower()
    if any(field in loc_text for field in ("timezone",)):
        code = "INVALID_TIMEZONE"
    elif any(field in loc_text for field in ("gender_val", "gender")):
        code = "INVALID_GENDER"
    elif any(field in loc_text for field in ("hour_val", "hour")):
        code = "INVALID_BIRTH_HOUR"
    elif any(field in loc_text for field in ("day", "month", "year")):
        code = "INVALID_BIRTH_DATE"
    else:
        code = "INVALID_INPUT"
    detail = "; ".join(f"{err.get('loc', [])}: {err.get('msg', 'invalid')}" for err in exc.errors())
    return JSONResponse(
        status_code=422,
        content={"error": {"code": code, "detail": detail}},
    )


app.include_router(health.router)
app.include_router(horoscope.router)
app.include_router(calendar.router)
app.include_router(auspicious.router)
