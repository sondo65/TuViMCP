# -*- coding: utf-8 -*-
"""Unit tests for per-activity auspicious scoring."""

from __future__ import annotations

import pytest

from tuvi_mcp._activity_catalog import ACTIVITY_ORDER, ACTIVITY_SLUGS
from tuvi_mcp._activity_rules import (
    JI_NOTHING_GOOD,
    KIM_THAN_THAT_SAT_CHI,
    NGOC_HAP_KY,
    TRUC_ACTIVITY_RULES,
    TRUC_CODES,
    XIU_ACTIVITY_RULES,
    XIU_CODES,
    YI_JI_ACTIVITY_MAP,
    YI_OTHERS_AVOIDED,
    hoang_dao_theo_thang,
    ngoc_hap_taboos,
)
from tuvi_mcp._activity_scorer import (
    classify_day_activities,
    score_activity,
    truc_verdict_for_activity,
    xiu_verdict_for_day,
)
from tuvi_mcp._auspicious import TRUC_MAP, XIU_MAP, get_auspicious_details


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
    assert isinstance(raw["viec_nen_lam"], list)
    assert isinstance(raw["viec_can_tranh"], list)


def _avoid_map(raw: dict) -> dict[str, list[str]]:
    return {item["slug"]: item["nguon"] for item in raw["viec_can_tranh"]}


def test_oct_7_2026_truc_chap_vetoes_travel_and_shop_opening():
    raw = get_auspicious_details(7, 10, 2026)
    assert raw["truc_ngay"]["ma"] == "chap"
    avoid = _avoid_map(raw)

    assert "truc" in avoid["xuat_hanh"]
    assert {"ngay_ky", "truc"} <= set(avoid["mo_hang"])
    assert "ngay_ky" in avoid["cuoi_hoi"]
    assert not set(raw["viec_nen_lam"]) & set(avoid)

    for slug in ("xuat_hanh", "mo_hang", "khai_truong", "cuoi_hoi"):
        dgv = get_auspicious_details(7, 10, 2026, activity=slug)["danh_gia_viec"]
        assert dgv["cat_percent"] < 40, slug
        assert dgv["danh_gia"].startswith("Hung")
        assert dgv["ly_do"]


def test_oct_9_2026_nothing_good_avoids_everything_outside_nghi():
    raw = get_auspicious_details(9, 10, 2026)
    avoid = _avoid_map(raw)
    nen = set(raw["viec_nen_lam"])
    assert nen == {"pha_do", "cung_le"}
    assert set(ACTIVITY_ORDER) - nen <= set(avoid)


def test_oct_13_2026_truc_khai_recommends_travel():
    raw = get_auspicious_details(13, 10, 2026)
    assert "xuat_hanh" in raw["viec_nen_lam"]
    dgv = get_auspicious_details(13, 10, 2026, activity="xuat_hanh")["danh_gia_viec"]
    assert dgv["cat_percent"] >= 60


def test_oct_13_2026_sao_duc_on_than_day_is_not_a_veto():
    # Canh Thân: "Sao Dực tại Thân, Tý, Thìn mọi việc tốt".
    raw = get_auspicious_details(13, 10, 2026)
    assert {"khai_truong", "cuoi_hoi"} <= set(raw["viec_nen_lam"])
    for slug in ("khai_truong", "cuoi_hoi"):
        dgv = get_auspicious_details(13, 10, 2026, activity=slug)["danh_gia_viec"]
        assert dgv["cat_percent"] >= 60, slug


def test_xiu_verdict_for_day_applies_branch_exceptions():
    duc = {"ten": "Sao Dực", "danh_gia": "Hung (Xấu)"}
    assert xiu_verdict_for_day(duc, "Thân") == "cat"
    assert xiu_verdict_for_day(duc, "Ngọ") == "hung"
    co = {"ten": "Sao Cơ", "danh_gia": "Cát (Tốt)"}
    assert xiu_verdict_for_day(co, "Thìn") == "hung"
    assert xiu_verdict_for_day(co, None) == "cat"


def test_oct_31_2026_yi_others_sentinel_is_not_a_veto():
    # Nghi list ends with "Việc Khác Không Nên"; unlisted activities are not vetoed.
    raw = get_auspicious_details(31, 10, 2026)
    avoid = _avoid_map(raw)
    assert "nhap_hoc" in raw["viec_nen_lam"]
    assert "cau_tai" not in avoid
    assert len(avoid) < len(ACTIVITY_ORDER)


def test_oct_31_2026_truc_dinh_avoids_travel_and_vi_on_dan_avoids_wedding():
    raw = get_auspicious_details(31, 10, 2026)
    avoid = _avoid_map(raw)
    # "Tránh ... di chuyển" covers both travel slugs.
    assert "truc" in avoid["xuat_hanh"]
    assert "truc" in avoid["di_xa"]
    # Sao Vị on a Dần day: no weddings or house building.
    assert "tu" in avoid["cuoi_hoi"]
    assert "tu" in avoid["sua_nha"]


def test_truc_dinh_ky_ket_is_not_read_as_ky_label():
    # "Kỵ" must not match inside "ký kết".
    truc = {
        "ten": "Trực Định",
        "danh_gia": "Cát (Tốt)",
        "loi_khuyen": "Tốt cho nhập học, ký kết, đính hôn, lập hợp đồng, chăn nuôi. "
        "Tránh kiện tụng, di chuyển.",
    }
    xiu = {"ten": "Sao Giác", "danh_gia": "Cát (Tốt)"}
    classification = classify_day_activities(truc, xiu, [], [])
    avoided = {item["slug"] for item in classification["can_tranh"]}
    assert "ky_hop_dong" not in avoided
    assert "ky_hop_dong" in classification["nen_lam"]


def test_phuc_doan_avoids_burial_and_travel():
    # 03/10/2026 Canh Tuất + Sao Vị: Phục Đoạn Sát.
    avoid = _avoid_map(get_auspicious_details(3, 10, 2026))
    for slug in ("tang_le", "xuat_hanh", "di_xa"):
        assert "tu" in avoid[slug], slug


def test_yi_ji_map_keys_exist_in_engine_catalog():
    from tuvi_mcp._lunar_calendar.util.LunarUtil import LunarUtil

    catalog = set(LunarUtil._LunarUtil__YI_JI)
    assert set(YI_JI_ACTIVITY_MAP) <= catalog
    assert {YI_OTHERS_AVOIDED, JI_NOTHING_GOOD} <= catalog
    mapped = set().union(*YI_JI_ACTIVITY_MAP.values())
    assert mapped <= set(ACTIVITY_ORDER)


def test_rules_cover_all_truc_and_xiu():
    assert set(TRUC_ACTIVITY_RULES) == set(TRUC_MAP) == set(TRUC_CODES)
    assert set(XIU_ACTIVITY_RULES) == set(XIU_MAP) == set(XIU_CODES)
    assert set(ACTIVITY_ORDER) == ACTIVITY_SLUGS - {"all"}
    for rules in (*TRUC_ACTIVITY_RULES.values(), *XIU_ACTIVITY_RULES.values()):
        assert not rules["nen"] & rules["ky"]
        assert rules["nen"] | rules["ky"] <= set(ACTIVITY_ORDER)


def test_ngoc_hap_taboos_lookup():
    # 25/8 Bính Ngọ, ngày Nhâm Tý: Kim Thần Thất Sát (năm Bính kỵ Tý Sửu Dần Mão).
    assert ngoc_hap_taboos(25, 8, "Nhâm", "Tý", "Bính") == ["Kim Thần Thất Sát"]
    # 27/8 Giáp Dần: Dương Công Kỵ + Tam Nương + Kim Thần Thất Sát.
    assert ngoc_hap_taboos(27, 8, "Giáp", "Dần", "Bính") == [
        "Dương Công Kỵ Nhật",
        "Tam Nương",
        "Kim Thần Thất Sát",
    ]
    # Leap months use the base month; 14/-9 Canh Ngọ: Sát Chủ + Nguyệt Kỵ.
    assert ngoc_hap_taboos(14, -9, "Canh", "Ngọ", "Bính") == ["Sát Chủ", "Nguyệt Kỵ"]
    assert ngoc_hap_taboos(9, 8, "Quý", "Mùi", "Giáp") == ["Thọ Tử", "Kim Thần Thất Sát"]
    assert ngoc_hap_taboos(4, 9, "Canh", "Thân", "Bính") == []


def test_ngoc_hap_keys_are_valid_slugs():
    for slugs in NGOC_HAP_KY.values():
        assert slugs is None or slugs <= set(ACTIVITY_ORDER)
    assert set(KIM_THAN_THAT_SAT_CHI) == {
        "Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý",
    }


def test_oct_5_2026_kim_than_and_vang_vong_avoid_major_works():
    raw = get_auspicious_details(5, 10, 2026, activity="all")
    names = [item["ten"] for item in raw["ngay_ky"]["items"]]
    assert "Kim Thần Thất Sát" in names and "Vãng Vong" in names
    avoid = _avoid_map(raw)
    for slug in ("dong_tho", "sua_nha", "nhap_trach", "tang_le", "cuoi_hoi", "xuat_hanh"):
        assert "ngoc_hap" in avoid[slug], slug
    assert raw["danh_gia_viec"]["cat_percent"] == 50


def test_thien_duc_lifts_kim_than_day_ceiling():
    # 19/10/2026 has Kim Thần Thất Sát but also Thiên Đức + Nguyệt Đức.
    raw = get_auspicious_details(19, 10, 2026)
    assert "Kim Thần Thất Sát" in [item["ten"] for item in raw["ngay_ky"]["items"]]
    classification = classify_day_activities(
        raw["truc_ngay"], raw["nhi_thap_bat_tu"], [], [], "Dần",
        ["Kim Thần Thất Sát"], ["Thiên Đức"],
    )
    assert classification["ky_ca_ngay"] == []
    classification = classify_day_activities(
        raw["truc_ngay"], raw["nhi_thap_bat_tu"], [], [], "Dần", ["Kim Thần Thất Sát"],
    )
    assert classification["ky_ca_ngay"] == ["Kim Thần Thất Sát"]


def test_oct_7_2026_hoang_dao_by_month_outranks_taboos_for_the_day():
    # 27/8 âm, ngày Dần: Hoàng Đạo by month, so the day is good overall while
    # Dương Công Kỵ / Tam Nương still forbid the major undertakings.
    raw = get_auspicious_details(7, 10, 2026, activity="all")
    avoid = _avoid_map(raw)
    for slug in ("cuoi_hoi", "khai_truong", "dong_tho", "xuat_hanh"):
        assert "ngoc_hap" in avoid[slug], slug
    assert "chua_benh" in raw["viec_nen_lam"]
    assert 60 <= raw["danh_gia_viec"]["cat_percent"] < 70


def test_hoang_dao_theo_thang_table():
    assert hoang_dao_theo_thang(8, "Dần") == "hoang_dao"
    assert hoang_dao_theo_thang(8, "Thân") == "hac_dao"
    assert hoang_dao_theo_thang(8, "Tý") is None
    # Hợi is in both columns of months 3/9: Hoàng wins.
    assert hoang_dao_theo_thang(9, "Hợi") == "hoang_dao"
    assert hoang_dao_theo_thang(-3, "Tuất") == "hac_dao"


def test_oct_2026_day_tiers_follow_the_by_month_table():
    tiers = {}
    for day in range(1, 32):
        pct = get_auspicious_details(day, 10, 2026, activity="all")["danh_gia_viec"]["cat_percent"]
        tiers[day] = "good" if pct >= 60 else ("bad" if pct < 40 else "neutral")
    assert {d for d, t in tiers.items() if t == "bad"} == {1, 4, 6, 12, 15, 18, 24, 27, 30}
    assert {2, 7, 8, 10, 14, 16, 21, 22, 26, 28} <= {d for d, t in tiers.items() if t == "good"}
    for day in (3, 5, 9, 11, 17, 20, 23, 29, 31):
        assert tiers[day] == "neutral", day


def test_avoided_activities_count_half_in_day_average():
    # 19/10/2026: Thiên Đức day where Kim Thần only forbids construction.
    raw = get_auspicious_details(19, 10, 2026, activity="all")
    assert raw["danh_gia_viec"]["cat_percent"] >= 60
    assert "cuoi_hoi" in raw["viec_nen_lam"]


def test_tam_nuong_caps_a_day_outside_the_hoang_dao_table():
    # 31/10/2026 = 22/9 âm, ngày Dần: neither Hoàng nor Hắc by month.
    raw = get_auspicious_details(31, 10, 2026, activity="all")
    assert raw["danh_gia_viec"]["cat_percent"] == 50


def test_tam_nuong_avoids_wedding_and_opening():
    # 02/10/2026 = 22/8 âm: Tam Nương.
    raw = get_auspicious_details(2, 10, 2026)
    assert raw["ngay_ky"]["items"][0]["ten"] == "Tam Nương"
    avoid = _avoid_map(raw)
    for slug in ("cuoi_hoi", "khai_truong", "xuat_hanh", "dong_tho"):
        assert "ngoc_hap" in avoid[slug], slug


def test_clean_days_keep_their_recommendations():
    # 13/10 and 25/10/2026 carry no Ngọc Hạp taboo and stay the month's best days.
    for day in (13, 25):
        raw = get_auspicious_details(day, 10, 2026, activity="all")
        assert raw["danh_gia_viec"]["cat_percent"] >= 90
        assert {"cuoi_hoi", "khai_truong", "xuat_hanh"} <= set(raw["viec_nen_lam"])
