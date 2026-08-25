# -*- coding: utf-8 -*-
"""Unit tests for per-activity auspicious scoring."""

from __future__ import annotations

import pytest

from tuvi_mcp._activity_scorer import score_activity, truc_verdict_for_activity
from tuvi_mcp._auspicious import TRUC_MAP, get_auspicious_details


def test_score_activity_all_is_activity_average():
    raw = get_auspicious_details(21, 8, 2026, activity="all")
    assert "danh_gia_viec" in raw
    dgv = raw["danh_gia_viec"]
    assert dgv["activity"] == "all"
    assert dgv["nguon"] == "activity_average"
    assert 0 <= dgv["cat_percent"] <= 100
    assert dgv["cat_percent"] <= 25  # golden: all Hung layers on 21/08/2026


def test_aug_10_2026_bach_ho_hac_dao():
    raw = get_auspicious_details(10, 8, 2026, activity="all")
    ngay = raw["ngay_hoang_dao"]
    assert ngay["ten_sao"] == "Bạch Hổ"
    assert ngay["loai"] == "Hắc Đạo"
    assert ngay["is_hoang_dao"] is False
    dgv = raw["danh_gia_viec"]
    assert 15 <= dgv["cat_percent"] <= 25  # ~17% vs competitors


def test_aug_22_2026_hoang_dao():
    raw = get_auspicious_details(22, 8, 2026, activity="all")
    assert raw["ngay_hoang_dao"]["loai"] == "Hoàng Đạo"
    assert raw["ngay_hoang_dao"]["is_hoang_dao"] is True


def test_truc_tru_ky_hop_dong_is_hung():
    truc = TRUC_MAP["Trừ"]
    verdict, source, keyword = truc_verdict_for_activity(truc, "ky_hop_dong")
    assert verdict == "hung"
    assert source == "truc_ngay"
    assert keyword is True


def test_truc_thanh_cuoi_hoi_is_cat():
    truc = TRUC_MAP["Thành"]
    verdict, _, keyword = truc_verdict_for_activity(truc, "cuoi_hoi")
    assert verdict == "cat"
    assert keyword is True


def test_ky_hop_dong_on_truc_tru_scores_hung():
    truc = TRUC_MAP["Trừ"]
    ngay = {"danh_gia": "Hung (Xấu)"}
    xiu = {"danh_gia": "Cát (Tốt)"}
    dgv = score_activity(truc, ngay, xiu, "ky_hop_dong")
    assert dgv["activity"] == "ky_hop_dong"
    assert "Hung" in dgv["danh_gia"]
    assert dgv["cat_percent"] < 40


def test_invalid_activity_slug_rejected_by_catalog():
    from tuvi_mcp._activity_catalog import is_valid_activity

    assert is_valid_activity("ky_hop_dong")
    assert is_valid_activity("nhap_hoc")
    assert not is_valid_activity("not_a_real_activity")


def test_nhap_hoc_scores_and_matches_keyword():
    raw = get_auspicious_details(17, 8, 2026, activity="nhap_hoc")
    dgv = raw["danh_gia_viec"]
    assert dgv["activity"] == "nhap_hoc"
    assert 0 <= dgv["cat_percent"] <= 100

    truc = TRUC_MAP["Thành"]
    verdict, source, keyword = truc_verdict_for_activity(truc, "nhap_hoc")
    assert keyword is True
    assert source == "truc_ngay"
    assert verdict == "cat"
    assert "nhập học" in truc["loi_khuyen"].lower()


def test_response_always_includes_danh_gia_viec():
    raw = get_auspicious_details(17, 8, 2026)
    assert "danh_gia_viec" in raw
    assert raw["danh_gia_viec"]["activity"] == "all"
