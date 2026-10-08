# -*- coding: utf-8 -*-
"""Language-neutral Nên / Kỵ rules per activity slug.

Three sources feed per-activity classification:

* the day's traditional Nghi / Kỵ list (``Lunar.getDayYi`` / ``getDayJi``),
* the 12 Trực,
* the 28 Tú (taboos only apply when the mansion is Hung on that day's branch,
  plus the per-branch "Ngoại lệ" and Phục Đoạn Sát taboos),
* Ngọc Hạp Thông Thư taboo days (Tam Nương, Nguyệt Kỵ, Kim Thần Thất Sát…).

Trực / Tú tables mirror the curated Vietnamese catalogs in the TuViAI app
(``truc_catalog_vi.dart`` / ``nhi_thap_bat_tu_catalog_vi.dart``).
"""

from __future__ import annotations

# 馀事勿取 in the Nghi list: only the listed items are recommended. Vietnamese
# almanacs do not read it as a taboo on everything else, so it is not a veto.
YI_OTHERS_AVOIDED = "Việc Khác Không Nên"
# 诸事不宜 in the Kỵ list: nothing is recommended — every unlisted activity is
# avoided.
JI_NOTHING_GOOD = "Không Có Việc Tốt"

# Engine Nghi / Kỵ item (``LunarUtil.__YI_JI``) -> activity slugs.
YI_JI_ACTIVITY_MAP: dict[str, frozenset[str]] = {
    "Cúng Tế": frozenset({"cung_le"}),
    "Cầu Phúc": frozenset({"cung_le"}),
    "Tạ Thần": frozenset({"cung_le"}),
    "Cầu Con": frozenset({"cau_tu"}),
    "Cưới Hỏi": frozenset({"cuoi_hoi"}),
    "Đính Hôn": frozenset({"cuoi_hoi"}),
    "Nạp Thải": frozenset({"cuoi_hoi"}),
    "Nạp Rể": frozenset({"cuoi_hoi"}),
    "An Táng": frozenset({"tang_le"}),
    "Nhập Liệm": frozenset({"tang_le"}),
    "Di Quan": frozenset({"tang_le"}),
    "Đám Tang": frozenset({"tang_le"}),
    "Nhập Trạch": frozenset({"nhap_trach"}),
    "Dọn Nhà": frozenset({"nhap_trach"}),
    "Sửa Chữa": frozenset({"sua_nha"}),
    "Xây Nhà": frozenset({"sua_nha"}),
    "Sửa Tường": frozenset({"sua_nha"}),
    "Lợp Mái Nhà": frozenset({"sua_nha"}),
    "Lợp Nhà": frozenset({"sua_nha"}),
    "Thượng Lương": frozenset({"sua_nha"}),
    "Khởi Công": frozenset({"dong_tho", "sua_nha"}),
    "Động Thổ": frozenset({"dong_tho"}),
    "Khởi Công Động Thổ": frozenset({"dong_tho"}),
    "Tháo Dỡ": frozenset({"pha_do"}),
    "Phá Nhà": frozenset({"pha_do"}),
    "Phá Tường": frozenset({"pha_do"}),
    "Phá Nhà Phá Tường": frozenset({"pha_do"}),
    "Khai Trương": frozenset({"khai_truong", "mo_hang", "bat_dau_cong_viec"}),
    "Treo Biển": frozenset({"khai_truong", "mo_hang"}),
    "Nạp Tài": frozenset({"cau_tai", "thu_no"}),
    "Cầu Tài": frozenset({"cau_tai"}),
    "Mở Kho": frozenset({"cau_tai", "vay_tien"}),
    "Xuất Hàng": frozenset({"vay_tien"}),
    "Giao Dịch": frozenset({"ky_hop_dong"}),
    "Lập Hợp Đồng": frozenset({"ky_hop_dong"}),
    "Ký Kết Giao Dịch": frozenset({"ky_hop_dong"}),
    "Xuất Hành": frozenset({"xuat_hanh", "di_xa"}),
    "Đi Thuyền": frozenset({"xuat_hanh", "di_xa"}),
    "Qua Sông": frozenset({"xuat_hanh", "di_xa"}),
    "Chữa Bệnh": frozenset({"chua_benh", "phau_thuat"}),
    "Tìm Thầy Thuốc": frozenset({"chua_benh"}),
    "Cầu Chữa Bệnh": frozenset({"chua_benh"}),
    "Châm Cứu": frozenset({"chua_benh"}),
    "Nhập Học": frozenset({"nhap_hoc"}),
    "Học Nghề": frozenset({"nhap_hoc"}),
    "Hội Họp Bạn Bè": frozenset({"hop_quan_trong", "gap_doi_tac"}),
    "Gặp Bạn": frozenset({"gap_doi_tac"}),
    "Gặp Quý Nhân": frozenset({"gap_doi_tac"}),
    "Nhận Chức": frozenset({"hop_quan_trong", "bat_dau_cong_viec"}),
}

# Slugs that share one taboo in tradition: avoiding one avoids the other.
_SLUG_TWINS: tuple[frozenset[str], ...] = (
    frozenset({"khai_truong", "mo_hang"}),
    frozenset({"xuat_hanh", "di_xa"}),
)


def expand_twins(slugs: set[str] | frozenset[str]) -> set[str]:
    out = set(slugs)
    for twins in _SLUG_TWINS:
        if out & twins:
            out |= twins
    return out


def _rule(nen: set[str], ky: set[str]) -> dict[str, frozenset[str]]:
    ky_full = expand_twins(ky)
    return {
        "nen": frozenset(expand_twins(nen) - ky_full),
        "ky": frozenset(ky_full),
    }


# Keys match ``TRUC_MAP`` (``Lunar.getZhiXing``).
TRUC_ACTIVITY_RULES: dict[str, dict[str, frozenset[str]]] = {
    "Kiến": _rule({"cau_tai", "cung_le", "khai_truong", "xuat_hanh"}, {"dong_tho", "tang_le"}),
    "Trừ": _rule({"chua_benh"}, {"cuoi_hoi", "khai_truong", "ky_hop_dong"}),
    "Mãn": _rule({"cau_tai", "cung_le", "xuat_hanh"}, {"cuoi_hoi"}),
    "Bình": _rule({"ky_hop_dong"}, set()),
    "Định": _rule({"cuoi_hoi", "ky_hop_dong", "sua_nha"}, {"chua_benh"}),
    "Chấp": _rule(
        {"chua_benh", "dong_tho", "ky_hop_dong"},
        {"khai_truong", "mo_hang", "xuat_hanh", "nhap_trach", "vay_tien", "cau_tai"},
    ),
    "Phá": _rule({"pha_do"}, {"cuoi_hoi", "khai_truong", "ky_hop_dong"}),
    "Nguy": _rule(set(), {"cuoi_hoi", "ky_hop_dong", "xuat_hanh"}),
    "Thành": _rule(
        {
            "chua_benh",
            "cuoi_hoi",
            "dong_tho",
            "khai_truong",
            "ky_hop_dong",
            "nhap_hoc",
            "tang_le",
            "thu_no",
            "xuat_hanh",
        },
        set(),
    ),
    "Thu": _rule({"thu_no"}, {"di_xa", "tang_le"}),
    "Khai": _rule({"chua_benh", "dong_tho", "khai_truong", "nhap_hoc", "xuat_hanh"}, {"tang_le"}),
    "Bế": _rule({"tang_le"}, {"cuoi_hoi", "khai_truong", "xuat_hanh"}),
}

# Keys match ``XIU_MAP`` (``Lunar.getXiu``). ``ky`` applies only on Hung mansions.
XIU_ACTIVITY_RULES: dict[str, dict[str, frozenset[str]]] = {
    "Giác": _rule({"khai_truong", "nhap_hoc", "xuat_hanh"}, {"dong_tho"}),
    "Cang": _rule(set(), {"cuoi_hoi", "khai_truong"}),
    "Đê": _rule(set(), {"cuoi_hoi", "dong_tho", "xuat_hanh"}),
    "Phòng": _rule({"cau_tai", "cuoi_hoi"}, set()),
    "Tâm": _rule(set(), {"cuoi_hoi", "mo_hang"}),
    "Vĩ": _rule({"cuoi_hoi", "khai_truong"}, set()),
    "Cơ": _rule({"cau_tai", "xuat_hanh"}, {"dong_tho", "tang_le"}),
    "Đẩu": _rule({"cau_tai"}, {"cuoi_hoi"}),
    "Ngưu": _rule(set(), {"cuoi_hoi", "khai_truong", "xuat_hanh"}),
    "Nữ": _rule(set(), {"cuoi_hoi"}),
    "Hư": _rule(set(), {"cuoi_hoi", "dong_tho", "khai_truong"}),
    "Nguy": _rule(set(), {"xuat_hanh"}),
    "Thất": _rule({"cuoi_hoi", "nhap_trach"}, set()),
    "Bích": _rule(set(), {"pha_do"}),
    "Khuê": _rule(set(), {"cuoi_hoi", "khai_truong", "ky_hop_dong"}),
    "Lâu": _rule({"cuoi_hoi"}, set()),
    "Vị": _rule({"cau_tai", "cuoi_hoi"}, {"dong_tho"}),
    "Mão": _rule(set(), {"cuoi_hoi", "khai_truong"}),
    "Tất": _rule({"cuoi_hoi"}, set()),
    "Chủy": _rule(set(), {"cuoi_hoi", "khai_truong"}),
    "Sâm": _rule({"xuat_hanh"}, set()),
    "Tỉnh": _rule(set(), set()),
    "Quỷ": _rule(set(), {"cuoi_hoi", "dong_tho", "khai_truong", "xuat_hanh"}),
    "Liễu": _rule(set(), {"cuoi_hoi"}),
    "Tinh": _rule(set(), {"cuoi_hoi", "khai_truong", "ky_hop_dong"}),
    "Trương": _rule({"cau_tai", "cuoi_hoi"}, set()),
    "Dực": _rule(set(), {"cuoi_hoi", "khai_truong"}),
    "Chẩn": _rule({"xuat_hanh"}, set()),
}

# Day-branch exceptions ("Ngoại lệ") of the 28 mansions: the mansion's verdict
# on days of these Earthly Branches. Hung mansions turn Cát ("trăm việc đều
# tốt") or neutral ("dùng việc nhỏ", "tốt vừa"); some Cát mansions turn Hung.
XIU_BRANCH_VERDICT: dict[str, dict[str, str]] = {
    "Cang": {"Hợi": "cat", "Mão": "cat", "Mùi": "cat"},
    "Đê": {"Thân": "cat", "Tý": "cat", "Thìn": "cat"},
    "Tâm": {"Dần": "neutral"},
    "Cơ": {"Thân": "hung", "Thìn": "hung", "Tý": "neutral"},
    "Đẩu": {"Tỵ": "neutral"},
    "Ngưu": {"Ngọ": "cat", "Tuất": "neutral"},
    "Hư": {"Thân": "cat", "Tý": "cat", "Thìn": "cat"},
    "Nguy": {"Tỵ": "cat", "Dậu": "cat", "Sửu": "cat"},
    "Bích": {"Hợi": "hung", "Mão": "hung", "Mùi": "hung"},
    "Khuê": {"Ngọ": "cat", "Thìn": "neutral"},
    "Mão": {"Mão": "cat"},
    "Chủy": {"Dậu": "cat", "Sửu": "cat"},
    "Quỷ": {"Tý": "neutral"},
    "Liễu": {"Ngọ": "cat", "Tỵ": "neutral"},
    "Tinh": {"Dần": "cat", "Ngọ": "cat", "Tuất": "cat"},
    "Dực": {"Thân": "cat", "Tý": "cat", "Thìn": "cat"},
}

# Activities a mansion's "Ngoại lệ" forbids on specific day branches,
# regardless of the mansion's verdict.
XIU_BRANCH_KY: dict[str, dict[str, frozenset[str]]] = {
    "Vĩ": {b: frozenset({"tang_le"}) for b in ("Hợi", "Mão", "Mùi")},
    "Hư": {b: frozenset({"tang_le"}) for b in ("Thân", "Tý")},
    "Vị": {"Dần": frozenset({"cuoi_hoi", "dong_tho", "nhap_trach", "sua_nha"})},
    "Liễu": {b: frozenset({"dong_tho", "sua_nha", "tang_le"}) for b in ("Dần", "Tuất")},
}

# Phục Đoạn Sát: day branch -> mansion. Avoid burial, departures, inheritance.
PHUC_DOAN_XIU: dict[str, str] = {
    "Tý": "Hư",
    "Sửu": "Đẩu",
    "Dần": "Thất",
    "Mão": "Nữ",
    "Thìn": "Cơ",
    "Tỵ": "Phòng",
    "Ngọ": "Giác",
    "Mùi": "Trương",
    "Thân": "Quỷ",
    "Dậu": "Chủy",
    "Tuất": "Vị",
    "Hợi": "Bích",
}
PHUC_DOAN_KY: frozenset[str] = frozenset({"tang_le", "xuat_hanh", "di_xa"})

# --- Ngọc Hạp Thông Thư taboo days (Vietnamese almanacs) ---------------------
# Months and days are lunar; a leap month uses its base month number.

# Major undertakings Tam Nương / Nguyệt Kỵ forbid.
_DAI_SU: frozenset[str] = frozenset(
    {
        "bat_dau_cong_viec",
        "cuoi_hoi",
        "di_xa",
        "dong_tho",
        "khai_truong",
        "ky_hop_dong",
        "mo_hang",
        "nhap_trach",
        "sua_nha",
        "xuat_hanh",
    }
)
_XAY_DUNG_AN_TANG: frozenset[str] = frozenset(
    {"dong_tho", "nhap_trach", "pha_do", "sua_nha", "tang_le"}
)

TAM_NUONG = "Tam Nương"
NGUYET_KY = "Nguyệt Kỵ"
DUONG_CONG_KY = "Dương Công Kỵ Nhật"
SAT_CHU = "Sát Chủ"
THO_TU = "Thọ Tử"
KIM_THAN_THAT_SAT = "Kim Thần Thất Sát"

TAM_NUONG_DAYS: frozenset[int] = frozenset({3, 7, 13, 18, 22, 27})
NGUYET_KY_DAYS: frozenset[int] = frozenset({5, 14, 23})
DUONG_CONG_KY_DAYS: frozenset[tuple[int, int]] = frozenset(
    {
        (1, 13), (2, 11), (3, 9), (4, 7), (5, 5), (6, 3), (7, 8),
        (7, 29), (8, 27), (9, 25), (10, 23), (11, 21), (12, 19),
    }
)
# Lunar month -> day branch.
SAT_CHU_CHI: dict[int, str] = {
    1: "Tỵ", 2: "Tý", 3: "Mùi", 4: "Mão", 5: "Thân", 6: "Tuất",
    7: "Sửu", 8: "Hợi", 9: "Ngọ", 10: "Dậu", 11: "Dần", 12: "Thìn",
}
# Lunar month -> day can chi.
THO_TU_CAN_CHI: dict[int, str] = {
    1: "Bính Tuất", 2: "Nhâm Thìn", 3: "Tân Hợi", 4: "Đinh Tỵ",
    5: "Mậu Tý", 6: "Bính Ngọ", 7: "Ất Sửu", 8: "Quý Mùi",
    9: "Giáp Dần", 10: "Mậu Thân", 11: "Tân Mão", 12: "Tân Dậu",
}
# Year stem -> day branches (Hứa Chân Quân Ngọc Hạp table).
KIM_THAN_THAT_SAT_CHI: dict[str, frozenset[str]] = {
    **dict.fromkeys(("Giáp", "Kỷ"), frozenset({"Ngọ", "Mùi"})),
    **dict.fromkeys(("Ất", "Canh"), frozenset({"Thìn", "Tỵ"})),
    **dict.fromkeys(("Bính", "Tân"), frozenset({"Tý", "Sửu", "Dần", "Mão"})),
    **dict.fromkeys(("Đinh", "Nhâm"), frozenset({"Tuất", "Hợi"})),
    **dict.fromkeys(("Mậu", "Quý"), frozenset({"Thân", "Dậu"})),
}

# Taboo -> avoided activities; ``None`` means every activity (bách kỵ).
NGOC_HAP_KY: dict[str, frozenset[str] | None] = {
    TAM_NUONG: _DAI_SU,
    NGUYET_KY: _DAI_SU,
    DUONG_CONG_KY: _DAI_SU,
    SAT_CHU: None,
    THO_TU: None,
    KIM_THAN_THAT_SAT: _XAY_DUNG_AN_TANG,
    # Hung sát already reported by the engine (``getDayXiongSha``).
    "Vãng Vong": frozenset({"cau_tai", "cuoi_hoi", "di_xa", "dong_tho", "xuat_hanh"}),
    "Hà Khôi": frozenset({"dong_tho", "sua_nha"}),
    "Thiên Cang": frozenset({"dong_tho", "sua_nha"}),
    "Thổ Phù": frozenset({"dong_tho"}),
    "Thổ Phủ": frozenset({"dong_tho"}),
    "Tiểu Hao": frozenset({"cau_tai", "khai_truong", "ky_hop_dong", "mo_hang"}),
    "Đại Hao": frozenset({"cau_tai", "khai_truong", "ky_hop_dong", "mo_hang"}),
}

# Taboo days almanacs rate as "hạn chế đại sự" overall: the whole-day score
# never reaches the good tier, whatever the individual activities score.
# "Tứ Phế" comes from the engine (``getDayXiongSha``).
DAY_CAP_TABOOS: frozenset[str] = frozenset(
    {TAM_NUONG, NGUYET_KY, DUONG_CONG_KY, SAT_CHU, THO_TU, KIM_THAN_THAT_SAT, "Tứ Phế"}
)
# Taboo -> cát thần (``getDayJiShen``) that lift its whole-day ceiling.
DAY_CAP_RESOLVERS: dict[str, frozenset[str]] = {
    KIM_THAN_THAT_SAT: frozenset({"Thiên Đức", "Nguyệt Đức"}),
}

# Vietnamese wall-calendar Hoàng / Hắc Đạo by lunar month and day branch
# (distinct from the 12 thần of ``getDayTianShen``). Hoàng wins when a branch
# is listed in both columns.
_HOANG_HAC_THEO_THANG: dict[int, tuple[frozenset[str], frozenset[str]]] = {
    1: (frozenset({"Tý", "Sửu", "Tỵ", "Mùi"}), frozenset({"Ngọ", "Mão", "Hợi", "Dậu"})),
    2: (frozenset({"Dần", "Mão", "Mùi", "Dậu"}), frozenset({"Thân", "Tỵ", "Sửu", "Hợi"})),
    3: (frozenset({"Thìn", "Tỵ", "Dậu", "Hợi"}), frozenset({"Tuất", "Mùi", "Sửu", "Hợi"})),
    4: (frozenset({"Ngọ", "Mùi", "Sửu", "Dậu"}), frozenset({"Tý", "Dậu", "Tỵ", "Mão"})),
    5: (frozenset({"Thân", "Dậu", "Sửu", "Mão"}), frozenset({"Dần", "Hợi", "Mùi", "Tỵ"})),
    6: (frozenset({"Tuất", "Hợi", "Mão", "Tỵ"}), frozenset({"Thìn", "Sửu", "Dậu", "Mùi"})),
}
HOANG_DAO = "hoang_dao"
HAC_DAO = "hac_dao"


def hoang_dao_theo_thang(lunar_month: int, day_chi: str) -> str | None:
    """``HOANG_DAO`` / ``HAC_DAO`` from the by-month table, else ``None``."""
    month = abs(lunar_month)
    hoang, hac = _HOANG_HAC_THEO_THANG.get((month - 1) % 6 + 1, (frozenset(), frozenset()))
    if day_chi in hoang:
        return HOANG_DAO
    if day_chi in hac:
        return HAC_DAO
    return None


def ngoc_hap_taboos(
    lunar_day: int,
    lunar_month: int,
    day_can: str,
    day_chi: str,
    year_can: str,
) -> list[str]:
    """Ngọc Hạp taboo-day names that fall on this day (not from the engine)."""
    month = abs(lunar_month)
    out: list[str] = []
    if (month, lunar_day) in DUONG_CONG_KY_DAYS:
        out.append(DUONG_CONG_KY)
    if THO_TU_CAN_CHI.get(month) == f"{day_can} {day_chi}":
        out.append(THO_TU)
    if SAT_CHU_CHI.get(month) == day_chi:
        out.append(SAT_CHU)
    if lunar_day in TAM_NUONG_DAYS:
        out.append(TAM_NUONG)
    if lunar_day in NGUYET_KY_DAYS:
        out.append(NGUYET_KY)
    if day_chi in KIM_THAN_THAT_SAT_CHI.get(year_can, frozenset()):
        out.append(KIM_THAN_THAT_SAT)
    return out

# Stable language-neutral codes (match the app catalog keys).
TRUC_CODES: dict[str, str] = {
    "Kiến": "kien",
    "Trừ": "tru",
    "Mãn": "man",
    "Bình": "binh",
    "Định": "dinh",
    "Chấp": "chap",
    "Phá": "pha",
    "Nguy": "nguy",
    "Thành": "thanh",
    "Thu": "thu",
    "Khai": "khai",
    "Bế": "be",
}

XIU_CODES: dict[str, str] = {
    "Giác": "giac",
    "Cang": "cang",
    "Đê": "de",
    "Phòng": "phong",
    "Tâm": "tam",
    "Vĩ": "vi",
    "Cơ": "co",
    "Đẩu": "dau",
    "Ngưu": "nguu",
    "Nữ": "nu",
    "Hư": "hu",
    "Nguy": "nguy",
    "Thất": "that",
    "Bích": "bich",
    "Khuê": "khue",
    "Lâu": "lau",
    "Vị": "vi_mansions",
    "Mão": "mao",
    "Tất": "tat",
    "Chủy": "chuy",
    "Sâm": "sam",
    "Tỉnh": "tinh_gieng",
    "Quỷ": "quy",
    "Liễu": "lieu",
    "Tinh": "tinh",
    "Trương": "truong",
    "Dực": "duc",
    "Chẩn": "chan",
}


def slugs_for_yi_ji(items: list[str] | None) -> set[str]:
    out: set[str] = set()
    for item in items or []:
        out |= YI_JI_ACTIVITY_MAP.get(item, frozenset())
    return out


__all__ = [
    "DAY_CAP_RESOLVERS",
    "DAY_CAP_TABOOS",
    "HAC_DAO",
    "HOANG_DAO",
    "JI_NOTHING_GOOD",
    "KIM_THAN_THAT_SAT_CHI",
    "NGOC_HAP_KY",
    "PHUC_DOAN_KY",
    "PHUC_DOAN_XIU",
    "TRUC_ACTIVITY_RULES",
    "TRUC_CODES",
    "XIU_ACTIVITY_RULES",
    "XIU_BRANCH_KY",
    "XIU_BRANCH_VERDICT",
    "XIU_CODES",
    "YI_JI_ACTIVITY_MAP",
    "YI_OTHERS_AVOIDED",
    "expand_twins",
    "hoang_dao_theo_thang",
    "ngoc_hap_taboos",
    "slugs_for_yi_ji",
]
