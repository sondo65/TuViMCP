# -*- coding: utf-8 -*-
"""Solar ↔ Lunar calendar conversion routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from tuvi_mcp import calendar as calendar_api
from tuvi_mcp._input import coerce_timezone, validate_calendar_convert
from tuvi_mcp.api.auth import require_supabase_jwt
from tuvi_mcp.api.errors import raise_from_engine_error, raise_http_error
from tuvi_mcp.api.schemas import CalendarConvertRequest

router = APIRouter(prefix="/v1", tags=["calendar"])


@router.post("/calendar", response_model=None)
def post_calendar(
    body: CalendarConvertRequest,
    _claims: dict = Depends(require_supabase_jwt),
):
    """Convert a date between Solar and Lunar calendars."""
    tz, tz_error = coerce_timezone(body.timezone, default=7.0)
    if tz_error is not None:
        raise_from_engine_error(tz_error)

    validation_error = validate_calendar_convert(
        body.day,
        body.month,
        body.year,
        from_solar=body.from_solar,
        lunar_leap=body.lunar_leap,
        timezone=tz,
    )
    if validation_error is not None:
        raise_from_engine_error(validation_error)

    if body.from_solar:
        result = calendar_api.convert_solar_to_lunar(
            body.day, body.month, body.year, timezone=tz
        )
    else:
        result = calendar_api.convert_lunar_to_solar(
            body.day,
            body.month,
            body.year,
            is_leap=body.lunar_leap,
            timezone=tz,
        )

    if isinstance(result, dict) and "error" in result:
        raise_from_engine_error(
            {
                "error": result["error"],
                "error_code": "INVALID_INPUT_PARAMETER",
                "details": [result["error"]],
                "suggestions": {"day": "Provide a valid calendar date."},
            }
        )

    return result
