# -*- coding: utf-8 -*-
"""Auspicious day / hour evaluation routes (FORT-03)."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends

from tuvi_mcp._activity_catalog import is_valid_activity
from tuvi_mcp._auspicious import get_auspicious_details
from tuvi_mcp._input import coerce_timezone
from tuvi_mcp.api.auth import require_supabase_jwt
from tuvi_mcp.api.errors import raise_from_engine_error, raise_http_error
from tuvi_mcp.api.schemas import AuspiciousRequest
from tuvi_mcp.horoscope import AuspiciousResult

router = APIRouter(prefix="/v1", tags=["auspicious"])


@router.post("/auspicious", response_model=None)
def post_auspicious(
    body: AuspiciousRequest,
    _claims: dict = Depends(require_supabase_jwt),
):
    """Evaluate Hoàng Đạo / Hắc Đạo, 12 Trực, 28 Tú, Tiết Khí, and hours for a date."""
    tz, tz_error = coerce_timezone(body.timezone, default=7.0)
    if tz_error is not None:
        raise_from_engine_error(tz_error)

    today = date.today()
    day = body.day if body.day is not None else today.day
    month = body.month if body.month is not None else today.month
    year = body.year if body.year is not None else today.year

    if not is_valid_activity(body.activity):
        raise_from_engine_error(
            {
                "error": f"Invalid activity slug: {body.activity!r}",
                "error_code": "INVALID_INPUT_PARAMETER",
                "details": [f"Unknown activity: {body.activity!r}"],
                "suggestions": {"activity": "Use a slug from the activity catalog or omit for general rating."},
            }
        )

    raw = get_auspicious_details(
        day,
        month,
        year,
        is_solar=body.is_solar,
        timezone=tz,
        activity=body.activity,
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
    except (KeyError, TypeError) as exc:
        raise_http_error(
            status_code=500,
            code="HOROSCOPE_ENGINE_ERROR",
            detail=str(exc),
        )
