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
    current_day: int | None = Field(default=None, ge=1, le=30)


class CalendarConvertRequest(BaseModel):
    """Solar ↔ Lunar conversion (no birth fields)."""

    day: int = Field(ge=1, le=31)
    month: int = Field(ge=1, le=12)
    year: int = Field(ge=1800, le=2100)
    from_solar: bool = True
    lunar_leap: bool = False
    timezone: int | float | str | None = 7


class AuspiciousRequest(BaseModel):
    """Auspicious day / hour evaluation for a calendar date or inclusive range (FORT-03)."""

    day: int | None = Field(default=None, ge=1, le=31)
    month: int | None = Field(default=None, ge=1, le=12)
    year: int | None = Field(default=None, ge=1800, le=2100)
    start_day: int | None = Field(default=None, ge=1, le=31)
    start_month: int | None = Field(default=None, ge=1, le=12)
    start_year: int | None = Field(default=None, ge=1800, le=2100)
    end_day: int | None = Field(default=None, ge=1, le=31)
    end_month: int | None = Field(default=None, ge=1, le=12)
    end_year: int | None = Field(default=None, ge=1800, le=2100)
    is_solar: bool = True
    timezone: int | float | str | None = 7
    activity: str | None = None

    @property
    def range_field_values(self) -> tuple[
        int | None,
        int | None,
        int | None,
        int | None,
        int | None,
        int | None,
    ]:
        return (
            self.start_day,
            self.start_month,
            self.start_year,
            self.end_day,
            self.end_month,
            self.end_year,
        )

    @property
    def has_complete_range(self) -> bool:
        return all(value is not None for value in self.range_field_values)

    @property
    def has_partial_range(self) -> bool:
        values = self.range_field_values
        present = sum(1 for value in values if value is not None)
        return 0 < present < len(values)
