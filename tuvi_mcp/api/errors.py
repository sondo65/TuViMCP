# -*- coding: utf-8 -*-
"""Map engine validation errors to stable REST error codes (D-05/D-06)."""

from __future__ import annotations

from fastapi import HTTPException

STABLE_CODES = frozenset(
    {
        "INVALID_BIRTH_DATE",
        "INVALID_BIRTH_HOUR",
        "INVALID_GENDER",
        "INVALID_TIMEZONE",
        "INVALID_INPUT",
        "HOROSCOPE_ENGINE_ERROR",
        "CHART_RENDER_ERROR",
        "CHART_IMAGE_NOT_FOUND",
    }
)


def _detail_message(engine_error: dict) -> str:
    details = engine_error.get("details")
    if isinstance(details, list) and details:
        return "; ".join(str(item) for item in details)
    if isinstance(engine_error.get("error"), str):
        return engine_error["error"]
    return "Input validation failed"


def map_engine_error_to_code(engine_error: dict) -> str:
    """Translate engine INVALID_INPUT_PARAMETER payloads to stable REST codes."""
    suggestions = engine_error.get("suggestions") or {}
    if isinstance(suggestions, dict):
        keys = {str(key).lower() for key in suggestions}
    else:
        keys = set()

    details_text = " ".join(str(item).lower() for item in engine_error.get("details") or [])

    if "timezone" in keys or "timezone" in details_text:
        return "INVALID_TIMEZONE"
    if "gender_val" in keys or "gender" in details_text:
        return "INVALID_GENDER"
    if "hour_val" in keys or "hour" in details_text:
        return "INVALID_BIRTH_HOUR"
    if any(token in keys for token in ("year", "month", "day")) or any(
        token in details_text for token in ("year", "month", "day", "date", "calendar")
    ):
        return "INVALID_BIRTH_DATE"
    return "INVALID_INPUT"


def raise_http_error(
    *,
    status_code: int,
    code: str,
    detail: str,
) -> None:
    if code not in STABLE_CODES:
        code = "INVALID_INPUT"
    raise HTTPException(
        status_code=status_code,
        detail={"error": {"code": code, "detail": detail}},
    )


def raise_from_engine_error(engine_error: dict, *, status_code: int = 400) -> None:
    code = map_engine_error_to_code(engine_error)
    raise_http_error(status_code=status_code, code=code, detail=_detail_message(engine_error))


def raise_from_value_error(exc: ValueError) -> None:
    message = str(exc).lower()
    if "gender" in message:
        code = "INVALID_GENDER"
    elif "hour" in message:
        code = "INVALID_BIRTH_HOUR"
    elif any(token in message for token in ("year", "month", "day", "calendar")):
        code = "INVALID_BIRTH_DATE"
    elif "timezone" in message:
        code = "INVALID_TIMEZONE"
    else:
        code = "HOROSCOPE_ENGINE_ERROR"
    status_code = 400 if code != "HOROSCOPE_ENGINE_ERROR" else 500
    raise_http_error(status_code=status_code, code=code, detail=str(exc))
