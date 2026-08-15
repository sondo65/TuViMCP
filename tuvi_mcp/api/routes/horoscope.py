# -*- coding: utf-8 -*-
"""Horoscope generation routes."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from tuvi_mcp import Horoscope
from tuvi_mcp._input import coerce_timezone, validate_birth_parameters
from tuvi_mcp.api.chart_images import resolve_chart_path, save_chart_png
from tuvi_mcp.api.errors import raise_from_engine_error, raise_from_value_error, raise_http_error
from tuvi_mcp.api.schemas import HoroscopeGenerateRequest
from tuvi_mcp.i18n import normalize_locale, t

router = APIRouter(prefix="/v1/horoscope", tags=["horoscope"])


@router.post("/generate", response_model=None)
def post_generate(body: HoroscopeGenerateRequest):
    """Generate a birth chart and return image_url + name."""
    tz, tz_error = coerce_timezone(body.timezone, default=7.0)
    if tz_error is not None:
        raise_from_engine_error(tz_error)

    try:
        locale = normalize_locale(body.locale)
    except ValueError:
        # Unwrapped D-06 envelope (same as RequestValidationError), not HTTPException.detail.
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "INVALID_LOCALE",
                    "detail": (
                        f"Unsupported locale: {body.locale!r}. "
                        "Allowed: vi, en, zh, ko, ja, ms"
                    ),
                }
            },
        )

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
        chart = horoscope.chart()

        view_year = body.current_year if body.current_year is not None else datetime.now().year
        temp_png_path = horoscope.render_chart(chart, year=view_year, locale=locale)

        # Save PNG to charts directory and get UUID
        chart_id = save_chart_png(temp_png_path)

        # Return relative image URL and name
        image_url = f"/v1/horoscope/images/{chart_id}.png"

        return {
            "image_url": image_url,
            "name": display_name,
        }
    except ValueError as exc:
        raise_from_value_error(exc)
    except Exception as exc:  # pragma: no cover - defensive engine guard
        # Check if this is a render error specifically
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


@router.get("/images/{chart_id}.png")
def get_chart_image(chart_id: str) -> FileResponse:
    """Serve PNG chart image by chart ID."""
    chart_path = resolve_chart_path(chart_id)
    if chart_path is None:
        raise_http_error(
            status_code=404,
            code="CHART_IMAGE_NOT_FOUND",
            detail=f"Chart image not found: {chart_id}",
        )
    
    return FileResponse(
        path=str(chart_path),
        media_type="image/png",
        filename=f"{chart_id}.png"
    )
