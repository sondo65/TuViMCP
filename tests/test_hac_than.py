# -*- coding: utf-8 -*-
"""Hạc Thần (taboo travel direction) on the 60-day Lục Thập Hoa Giáp cycle."""

from __future__ import annotations

from collections import Counter

import pytest

from tuvi_mcp._auspicious import get_auspicious_details, hac_than_direction


@pytest.mark.parametrize(
    ("index", "expected"),
    [
        (44, None),  # Mậu Thân: last heaven day
        (45, "Đông Bắc"),  # Kỷ Dậu
        (50, "Đông Bắc"),  # Giáp Dần
        (51, "Chính Đông"),  # Ất Mão
        (55, "Chính Đông"),  # Kỷ Mùi
        (56, "Đông Nam"),  # Canh Thân
        (1, "Đông Nam"),  # Ất Sửu (wraps past Giáp Tý)
        (2, "Chính Nam"),  # Bính Dần
        (7, "Tây Nam"),  # Tân Mùi
        (13, "Chính Tây"),  # Đinh Sửu
        (18, "Tây Bắc"),  # Nhâm Ngọ
        (24, "Chính Bắc"),  # Mậu Tý
        (28, "Chính Bắc"),  # Nhâm Thìn
        (29, None),  # Quý Tỵ: goes up to heaven
    ],
)
def test_segment_boundaries(index, expected):
    assert hac_than_direction(index) == expected


def test_full_cycle_distribution():
    counts = Counter(hac_than_direction(i) for i in range(60))
    assert counts[None] == 16
    for corner in ("Đông Bắc", "Đông Nam", "Tây Nam", "Tây Bắc"):
        assert counts[corner] == 6
    for cardinal in ("Chính Đông", "Chính Nam", "Chính Tây", "Chính Bắc"):
        assert counts[cardinal] == 5


def test_invalid_index_has_no_direction():
    assert hac_than_direction(-1) is None
    assert hac_than_direction(60) is None


@pytest.mark.parametrize(
    ("day", "month", "can_chi", "direction"),
    [
        (27, 7, "Nhâm Dần", None),
        (3, 8, "Kỷ Dậu", "Đông Bắc"),
        (9, 8, "Ất Mão", "Chính Đông"),
        (17, 7, "Nhâm Thìn", "Chính Bắc"),
        (18, 7, "Quý Tỵ", None),
    ],
)
def test_auspicious_payload(day, month, can_chi, direction):
    raw = get_auspicious_details(day, month, 2026)
    assert "error" not in raw
    assert raw["can_chi_ngay"].startswith(can_chi)
    huong = raw["huong_xuat_hanh"]
    assert huong["hac_than"] == (direction or "")
    assert huong["hac_than_tren_troi"] is (direction is None)
