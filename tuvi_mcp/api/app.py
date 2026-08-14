# -*- coding: utf-8 -*-
"""FastAPI application entry point."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from tuvi_mcp.api.routes import health, horoscope

app = FastAPI(title="TuViMCP REST")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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
