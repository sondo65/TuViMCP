# -*- coding: utf-8 -*-
"""Unit + contract coverage for ngu_hanh / ngay_ky on auspicious."""

from __future__ import annotations

from tuvi_mcp._auspicious import get_auspicious_details


def test_ngu_hanh_golden_2026_08_26_without_menh():
    raw = get_auspicious_details(26, 8, 2026)
    assert "error" not in raw
    ngu = raw["ngu_hanh"]
    assert ngu["can_chi"] == "Nhâm Thân"
    assert ngu["can_hanh"] == "Thủy"
    assert ngu["chi_hanh"] == "Kim"
    assert ngu["nap_am"] == "Kiếm Phong Kim"
    assert "quan_he_can_chi" in ngu
    assert "loi_khuyen" in ngu
    assert "quan_he_menh" not in ngu
    assert "menh" not in ngu

    ky = raw["ngay_ky"]
    assert ky["pham_ky"] is True
    assert isinstance(ky["items"], list) and len(ky["items"]) >= 1
    assert all("ten" in item and "loi_khuyen" in item for item in ky["items"])
    assert isinstance(ky["viec_ky"], list)


def test_ngu_hanh_with_menh_sets_quan_he_menh():
    raw = get_auspicious_details(26, 8, 2026, menh="K")
    ngu = raw["ngu_hanh"]
    assert ngu["menh"] == "K"
    assert ngu["menh_hanh"] == "Kim"
    assert "quan_he_menh" in ngu
    assert ngu["quan_he_menh_code"] == "binh_hoa"
