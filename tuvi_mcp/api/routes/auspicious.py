# -*- coding: utf-8 -*-
"""Auspicious day / hour evaluation routes (FORT-03)."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends

from tuvi_mcp._activity_catalog import is_valid_activity
from tuvi_mcp._auspicious import get_auspicious_details
from tuvi_mcp._input import coerce_timezone
from tuvi_mcp.api.auth import require_supabase_jwt
from tuvi_mcp.api.errors import raise_from_engine_error, raise_http_error
from tuvi_mcp.api.schemas import AuspiciousRequest
from tuvi_mcp.horoscope import AuspiciousResult

router = APIRouter(prefix="/v1", tags=["auspicious"])

# Max inclusive span for range requests (covers ~2 calendar months).
_MAX_RANGE_DAYS = 62


def _result_dict_from_raw(raw: dict) -> dict:
    return AuspiciousResult(
        duong_lich=raw["duong_lich"],
        am_lich=raw["am_lich"],
        can_chi_ngay=raw["can_chi_ngay"],
        ngay_hoang_dao=raw["ngay_hoang_dao"],
        truc_ngay=raw["truc_ngay"],
        nhi_thap_bat_tu=raw["nhi_thap_bat_tu"],
        huong_xuat_hanh=raw["huong_xuat_hanh"],
        gio_hoang_dao=raw["gio_hoang_dao"],
        tiet_khi_hien_tai=raw.get("tiet_khi_hien_tai", "N/A"),
        tiet_khi_tiep_theo=raw.get("tiet_khi_tiep_theo", "N/A"),
        danh_gia_viec=raw.get("danh_gia_viec", {}),
    ).to_dict()


def _evaluate_one_day(
    *,
    day: int,
    month: int,
    year: int,
    is_solar: bool,
    timezone: float,
    activity: str | None,
) -> dict:
    raw = get_auspicious_details(
        day,
        month,
        year,
        is_solar=is_solar,
        timezone=timezone,
        activity=activity,
    )
    if isinstance(raw, dict) and "error" in raw:
        raise_from_engine_error(
            {
                "error": raw["error"],
                "error_code": "INVALID_INPUT_PARAMETER",
                "details": [raw["error"]],
                "suggestions": {"day": "Provide a valid calendar date."},
            }
        )
    try:
        return _result_dict_from_raw(raw)
    except (KeyError, TypeError) as exc:
        raise_http_error(
            status_code=500,
            code="HOROSCOPE_ENGINE_ERROR",
            detail=str(exc),
        )


def _parse_calendar_date(day: int, month: int, year: int, *, field: str) -> date:
    try:
        return date(year, month, day)
    except ValueError as exc:
        raise_from_engine_error(
            {
                "error": f"Invalid {field} date: {day:02d}/{month:02d}/{year}",
                "error_code": "INVALID_INPUT_PARAMETER",
                "details": [str(exc)],
                "suggestions": {
                    field: "Provide a valid calendar day/month/year.",
                },
            }
        )


@router.post("/auspicious", response_model=None)
def post_auspicious(
    body: AuspiciousRequest,
    _claims: dict = Depends(require_supabase_jwt),
):
    """Evaluate Hoàng Đạo / Hắc Đạo, 12 Trực, 28 Tú, Tiết Khí, and hours.

    Single-day body (``day``/``month``/``year``, or defaults to today) returns a
    flat object. Inclusive range via ``start_*`` + ``end_*`` returns
    ``{"days": [...]}``.
    """
    tz, tz_error = coerce_timezone(body.timezone, default=7.0)
    if tz_error is not None:
        raise_from_engine_error(tz_error)

    if not is_valid_activity(body.activity):
        raise_from_engine_error(
            {
                "error": f"Invalid activity slug: {body.activity!r}",
                "error_code": "INVALID_INPUT_PARAMETER",
                "details": [f"Unknown activity: {body.activity!r}"],
                "suggestions": {
                    "activity": "Use a slug from the activity catalog or omit for general rating."
                },
            }
        )

    if body.has_partial_range:
        raise_from_engine_error(
            {
                "error": "Incomplete auspicious range: provide all start_* and end_* fields",
                "error_code": "INVALID_INPUT_PARAMETER",
                "details": [
                    "start_day, start_month, start_year, end_day, end_month, and end_year are all required for a range request."
                ],
                "suggestions": {
                    "start_day": "Send the full start/end sextet, or omit all range fields for a single day.",
                },
            }
        )

    if body.has_complete_range:
        start = _parse_calendar_date(
            body.start_day,  # type: ignore[arg-type]
            body.start_month,  # type: ignore[arg-type]
            body.start_year,  # type: ignore[arg-type]
            field="start",
        )
        end = _parse_calendar_date(
            body.end_day,  # type: ignore[arg-type]
            body.end_month,  # type: ignore[arg-type]
            body.end_year,  # type: ignore[arg-type]
            field="end",
        )
        if end < start:
            raise_from_engine_error(
                {
                    "error": "end date must be on or after start date",
                    "error_code": "INVALID_INPUT_PARAMETER",
                    "details": ["end date is before start date"],
                    "suggestions": {
                        "end_day": "Ensure end_* is greater than or equal to start_*.",
                    },
                }
            )
        span_days = (end - start).days + 1
        if span_days > _MAX_RANGE_DAYS:
            raise_from_engine_error(
                {
                    "error": f"auspicious range too large: {span_days} days (max {_MAX_RANGE_DAYS})",
                    "error_code": "INVALID_INPUT_PARAMETER",
                    "details": [
                        f"Inclusive span is {span_days} days; maximum allowed is {_MAX_RANGE_DAYS}."
                    ],
                    "suggestions": {
                        "end_day": f"Request at most {_MAX_RANGE_DAYS} inclusive days.",
                    },
                }
            )

        days_out: list[dict] = []
        cursor = start
        while cursor <= end:
            days_out.append(
                _evaluate_one_day(
                    day=cursor.day,
                    month=cursor.month,
                    year=cursor.year,
                    is_solar=body.is_solar,
                    timezone=tz,
                    activity=body.activity,
                )
            )
            cursor += timedelta(days=1)
        return {"days": days_out}

    today = date.today()
    day = body.day if body.day is not None else today.day
    month = body.month if body.month is not None else today.month
    year = body.year if body.year is not None else today.year
    return _evaluate_one_day(
        day=day,
        month=month,
        year=year,
        is_solar=body.is_solar,
        timezone=tz,
        activity=body.activity,
    )
