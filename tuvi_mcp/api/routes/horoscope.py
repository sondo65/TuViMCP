# -*- coding: utf-8 -*-
"""Horoscope generation routes."""

from __future__ import annotations

from fastapi import APIRouter

from tuvi_mcp import Horoscope
from tuvi_mcp._input import coerce_timezone, validate_birth_parameters
from tuvi_mcp.api.errors import raise_from_engine_error, raise_from_value_error, raise_http_error
from tuvi_mcp.api.schemas import HoroscopeGenerateRequest

router = APIRouter(prefix="/v1/horoscope", tags=["horoscope"])


@router.post("/generate")
def post_generate(body: HoroscopeGenerateRequest) -> dict:
    """Generate a birth chart as raw JSON (thien_ban, dia_ban, cach_cuc)."""
    tz, tz_error = coerce_timezone(body.timezone, default=7.0)
    if tz_error is not None:
        raise_from_engine_error(tz_error)

    validation_error = validate_birth_parameters(
        day=body.day,
        month=body.month,
        year=body.year,
        hour_val=body.hour_val,
        gender_val=body.gender_val,
        is_solar=body.is_solar,
        timezone=tz,
    )
    if validation_error is not None:
        raise_from_engine_error(validation_error)

    try:
        chart = Horoscope.from_birth(
            name=body.name or "Khách",
            year=body.year,
            month=body.month,
            day=body.day,
            hour=body.hour_val,
            gender=body.gender_val,
            calendar="solar" if body.is_solar else "lunar",
            timezone=tz,
        ).chart().to_dict()
    except ValueError as exc:
        raise_from_value_error(exc)
    except Exception as exc:  # pragma: no cover - defensive engine guard
        raise_http_error(
            status_code=500,
            code="HOROSCOPE_ENGINE_ERROR",
            detail=str(exc),
        )
    return chart
