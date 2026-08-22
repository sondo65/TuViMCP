# -*- coding: utf-8 -*-
"""Activity catalog for per-task auspicious day scoring (Nhật Vận)."""

from __future__ import annotations

# Slugs exposed via POST /v1/auspicious `activity` param.
# "all" = mean cat_percent across all per-activity slugs below.
ACTIVITY_ALL = "all"

ACTIVITY_SLUGS: frozenset[str] = frozenset(
    {
        ACTIVITY_ALL,
        "cau_tai",
        "cau_tu",
        "gap_doi_tac",
        "hop_quan_trong",
        "khai_truong",
        "ky_hop_dong",
        "mo_hang",
        "nhap_trach",
        "pha_do",
        "phau_thuat",
        "bat_dau_cong_viec",
        "chua_benh",
        "cung_le",
        "cuoi_hoi",
        "sua_nha",
        "tang_le",
        "thu_no",
        "vay_tien",
        "xuat_hanh",
        "di_xa",
        "dong_tho",
    }
)

# Vietnamese keywords to match inside truc_ngay.loi_khuyen (lowercase).
ACTIVITY_KEYWORDS: dict[str, list[str]] = {
    "cau_tai": ["cầu tài", "mở kho"],
    "cau_tu": ["cầu tự", "cầu con", "sinh con"],
    "gap_doi_tac": ["gặp đối tác", "đối tác", "hòa giải"],
    "hop_quan_trong": ["họp", "nhậm chức", "hội họp"],
    "khai_truong": ["khai trương", "mở cửa hàng", "mở hàng"],
    "ky_hop_dong": ["ký kết", "ký hợp đồng", "hợp đồng", "lập hợp đồng"],
    "mo_hang": ["mở cửa hàng", "mở hàng", "khai trương"],
    "nhap_trach": ["nhập trạch", "nhập học", "dọn nhà"],
    "pha_do": ["phá dỡ", "phá vỡ", "dỡ nhà", "giải táng"],
    "phau_thuat": ["phẫu thuật", "khám bệnh", "chữa bệnh", "giải phẫu"],
    "bat_dau_cong_viec": [
        "bắt đầu công việc",
        "khởi công",
        "nhậm chức",
        "xuất hành",
    ],
    "chua_benh": ["chữa bệnh", "giải trừ tai ạch", "khám bệnh", "tẩy uế"],
    "cung_le": ["cúng lễ", "cúng tế", "tế lễ", "cầu an"],
    "cuoi_hoi": ["cưới hỏi", "kết hôn", "đính hôn", "hôn nhân"],
    "sua_nha": ["sửa nhà", "sửa đường", "xây dựng", "làm nhà", "khởi công"],
    "tang_le": ["tang lễ", "an táng", "mai táng", "đắp mộ"],
    "thu_no": ["thu nợ", "thu hoạch", "thu hồi nợ"],
    "vay_tien": ["vay tiền", "xuất tiền", "mở kho", "cho vay"],
    "xuat_hanh": ["xuất hành", "đi thuyền", "du lịch"],
    "di_xa": ["đi xa", "xuất hành", "di chuyển", "trèo cao"],
    "dong_tho": ["động thổ", "đắp đập", "khởi công", "xây dựng"],
}


def normalize_activity(activity: str | None) -> str:
    """Return canonical slug or ACTIVITY_ALL."""
    if activity is None:
        return ACTIVITY_ALL
    slug = activity.strip().lower()
    if not slug or slug == ACTIVITY_ALL:
        return ACTIVITY_ALL
    return slug


def is_valid_activity(activity: str | None) -> bool:
    if activity is None:
        return True
    slug = activity.strip().lower()
    if not slug:
        return True
    return slug in ACTIVITY_SLUGS


__all__ = [
    "ACTIVITY_ALL",
    "ACTIVITY_KEYWORDS",
    "ACTIVITY_SLUGS",
    "is_valid_activity",
    "normalize_activity",
]
