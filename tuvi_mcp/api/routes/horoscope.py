# -*- coding: utf-8 -*-
"""Horoscope generation routes."""

from __future__ import annotations

from datetime import datetime
from typing import Union

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from tuvi_mcp import Horoscope
from tuvi_mcp._input import coerce_timezone, validate_birth_parameters
from tuvi_mcp.api.auth import require_supabase_jwt
from tuvi_mcp.api.chart_images import encode_png_base64
from tuvi_mcp.api.errors import raise_from_engine_error, raise_from_value_error, raise_http_error
from tuvi_mcp.api.schemas import HoroscopeGenerateRequest, HoroscopeTransitRequest
from tuvi_mcp.i18n import normalize_locale, t

router = APIRouter(prefix="/v1/horoscope", tags=["horoscope"])

BirthRequestBody = Union[HoroscopeGenerateRequest, HoroscopeTransitRequest]


def _build_horoscope(body: BirthRequestBody) -> tuple[Horoscope, str]:
    """Validate birth params and construct a Horoscope instance."""
    tz, tz_error = coerce_timezone(body.timezone, default=7.0)
    if tz_error is not None:
        raise_from_engine_error(tz_error)

    try:
        locale = normalize_locale(body.locale)
    except ValueError:
        raise ValueError("INVALID_LOCALE")

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

    display_name = body.name if body.name else t(locale, "Khách", section="ui")
    horoscope = Horoscope.from_birth(
        name=display_name,
        year=body.year,
        month=body.month,
        day=body.day,
        hour=body.hour_val,
        gender=body.gender_val,
        calendar="solar" if body.is_solar else "lunar",
        timezone=tz,
    )
    return horoscope, locale


def _invalid_locale_response(body_locale: str | None) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "INVALID_LOCALE",
                "detail": (
                    f"Unsupported locale: {body_locale!r}. "
                    "Allowed: vi, en, zh, ko, ja, ms"
                ),
            }
        },
    )


@router.post("/generate", response_model=None)
def post_generate(body: HoroscopeGenerateRequest, _claims: dict = Depends(require_supabase_jwt)):
    """Generate a birth chart and return image_base64 + name (no server-side PNG persist)."""
    try:
        horoscope, locale = _build_horoscope(body)
    except ValueError:
        return _invalid_locale_response(body.locale)

    try:
        chart = horoscope.chart()

        view_year = body.current_year if body.current_year is not None else datetime.now().year
        temp_png_path = horoscope.render_chart(chart, year=view_year, locale=locale)
        image_base64 = encode_png_base64(temp_png_path, delete_source=True)

        return {
            "image_base64": image_base64,
            "name": body.name if body.name else t(locale, "Khách", section="ui"),
        }
    except ValueError as exc:
        raise_from_value_error(exc)
    except Exception as exc:  # pragma: no cover - defensive engine guard
        if "render" in str(exc).lower():
            raise_http_error(
                status_code=500,
                code="CHART_RENDER_ERROR",
                detail=str(exc),
            )
        raise_http_error(
            status_code=500,
            code="HOROSCOPE_ENGINE_ERROR",
            detail=str(exc),
        )


@router.post("/chart", response_model=None)
def post_chart(body: HoroscopeGenerateRequest, _claims: dict = Depends(require_supabase_jwt)):
    """Return chart JSON (dia_ban / thien_ban) without PNG render (D-12)."""
    try:
        horoscope, _locale = _build_horoscope(body)
    except ValueError:
        return _invalid_locale_response(body.locale)

    try:
        return horoscope.chart().to_dict()
    except ValueError as exc:
        raise_from_value_error(exc)
    except Exception as exc:  # pragma: no cover - defensive engine guard
        raise_http_error(
            status_code=500,
            code="HOROSCOPE_ENGINE_ERROR",
            detail=str(exc),
        )


@router.post("/transit", response_model=None)
def post_transit(body: HoroscopeTransitRequest, _claims: dict = Depends(require_supabase_jwt)):
    """Return transit JSON for the requested year/month (D-15)."""
    try:
        horoscope, _locale = _build_horoscope(body)
    except ValueError:
        return _invalid_locale_response(body.locale)

    try:
        month = body.current_month or 1
        return horoscope.transit(year=body.current_year, month=month).to_dict()
    except ValueError as exc:
        raise_from_value_error(exc)
    except Exception as exc:  # pragma: no cover - defensive engine guard
        raise_http_error(
            status_code=500,
            code="HOROSCOPE_ENGINE_ERROR",
            detail=str(exc),
        )


