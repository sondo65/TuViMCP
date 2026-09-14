# -*- coding: utf-8 -*-
"""Golden tests for classical nguyệt hạn month ↔ palace mapping."""

from __future__ import annotations

from tuvi_mcp import tuvi_calculator
from tuvi_mcp._transit import (
    birth_hour_branch_from_thien_ban,
    birth_lunar_month_from_thien_ban,
    nguyet_han_month_by_cung,
)

# Đỗ Trường Sơn — solar 20/5/1995, hour Mậu Tuất (19:30)
_SON_PARAMS = dict(
    name="Đỗ Trường Sơn",
    day=20,
    month=5,
    year=1995,
    hour_val="19:30",
    gender_val="Nam",
    is_solar=True,
)


def test_do_truong_son_2026_month_7_phuc_duc_month_8_dien_trach():
    """Altuv-aligned: T.7 = Phúc đức / Thái âm, T.8 = Điền trạch / Tham lang."""
    m7 = tuvi_calculator.get_van_han_analysis(
        **_SON_PARAMS, current_year=2026, current_month=7
    )
    assert m7["nguyet_han"]["cung_chu"] == "Phúc đức"
    assert m7["nguyet_han"]["cung_so"] == 10
    assert any(s["name"] == "Thái âm" for s in m7["nguyet_han"]["sao"])

    m8 = tuvi_calculator.get_van_han_analysis(
        **_SON_PARAMS, current_year=2026, current_month=8
    )
    assert m8["nguyet_han"]["cung_chu"] == "Điền trạch"
    assert m8["nguyet_han"]["cung_so"] == 11
    assert any(s["name"] == "Tham lang" for s in m8["nguyet_han"]["sao"])


def test_nguyet_han_month_by_cung_matches_van_han_all_months():
    """Renderer month labels must be the inverse of get_van_han for all 12 months."""
    chart = tuvi_calculator.get_horoscope_chart(**_SON_PARAMS)
    thien_ban = chart["thien_ban"]
    birth_month = birth_lunar_month_from_thien_ban(thien_ban)
    birth_hour = birth_hour_branch_from_thien_ban(thien_ban)
    assert birth_month == 4  # lunar 21/4/1995
    assert birth_hour == 11  # Tuất

    month_by_cung = nguyet_han_month_by_cung(
        chart["dia_ban"],
        current_year=2026,
        birth_lunar_month=birth_month,
        birth_hour_branch=birth_hour,
    )
    assert len(month_by_cung) == 12
    assert set(month_by_cung.keys()) == set(range(1, 13))
    assert set(month_by_cung.values()) == set(range(1, 13))

    for month in range(1, 13):
        van = tuvi_calculator.get_van_han_analysis(
            **_SON_PARAMS, current_year=2026, current_month=month
        )
        cung_so = van["nguyet_han"]["cung_so"]
        assert month_by_cung[cung_so] == month


def test_static_branch_month_would_mislabel_phuc_duc_as_month_8():
    """Regression guard: old (cung_so-3)%12+1 puts Tháng 8 on Dậu/Phúc đức."""
    chart = tuvi_calculator.get_horoscope_chart(**_SON_PARAMS)
    phuc = next(c for c in chart["dia_ban"] if c["cung_chu"] == "Phúc đức")
    static_month = (phuc["cung_so"] - 3) % 12 + 1
    assert static_month == 8  # the old wrong label

    month_by_cung = nguyet_han_month_by_cung(
        chart["dia_ban"],
        current_year=2026,
        birth_lunar_month=birth_lunar_month_from_thien_ban(chart["thien_ban"]),
        birth_hour_branch=birth_hour_branch_from_thien_ban(chart["thien_ban"]),
    )
    assert month_by_cung[phuc["cung_so"]] == 7
