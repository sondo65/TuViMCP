# -*- coding: utf-8 -*-
"""Pydantic request/response schemas for the REST API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HoroscopeBirthFields(BaseModel):
    """Shared birth input fields for generate/chart/transit (D-01)."""

    name: str = "Khách"
    day: int = Field(ge=1, le=31)
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=1800, le=2100)
    hour_val: str = "12:00"
    gender_val: str = "Nam"
    is_solar: bool = True
    timezone: int | float | str | None = 7
    locale: str | None = None


class HoroscopeGenerateRequest(HoroscopeBirthFields):
    """Birth input mirroring MCP/library params (D-01)."""

    current_year: int | None = Field(default=None, ge=1800, le=2100)


class HoroscopeTransitRequest(HoroscopeBirthFields):
    """Birth input plus transit period for POST /transit (D-15)."""

    current_year: int = Field(ge=1800, le=2100)
    current_month: int = Field(default=1, ge=1, le=12)
