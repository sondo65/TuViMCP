# -*- coding: utf-8 -*-
"""Per-activity Cát/Hung scoring from auspicious day layers."""

from __future__ import annotations

import re
import unicodedata

from ._activity_catalog import (
    ACTIVITY_ALL,
    ACTIVITY_KEYWORDS,
    ACTIVITY_SLUGS,
    normalize_activity,
)

# Mirrors TIAN_SHEN_LUCK_MAP / truc danh_gia parsing in _auspicious.py
_VERDICT_CAT = "cat"
_VERDICT_HUNG = "hung"
_VERDICT_NEUTRAL = "neutral"

_DANH_GIA_LABEL = {
    _VERDICT_CAT: "Cát (Tốt)",
    _VERDICT_HUNG: "Hung (Xấu)",
    _VERDICT_NEUTRAL: "Bình (Bình thường)",
}


def _fold(text: str) -> str:
    """Lowercase + strip accents for Vietnamese keyword matching."""
    lowered = text.lower()
    normalized = unicodedata.normalize("NFD", lowered)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def parse_danh_gia(raw: str | None) -> str:
    """Return verdict token: cat, hung, or neutral."""
    normalized = _fold(raw or "")
    if not normalized:
        return _VERDICT_NEUTRAL
    if "cat" in normalized or "tốt" in normalized or "tot" in normalized:
        return _VERDICT_CAT
    if "hung" in normalized or "xấu" in normalized or "xau" in normalized:
        return _VERDICT_HUNG
    if "bình" in normalized or "binh" in normalized:
        return _VERDICT_NEUTRAL
    return _VERDICT_NEUTRAL


def _verdict_score(verdict: str) -> float:
    if verdict == _VERDICT_CAT:
        return 100.0
    if verdict == _VERDICT_HUNG:
        return 0.0
    return 50.0


def _segment_after(label: str, text: str) -> str:
    """Text after a label until the next sentence boundary marker."""
    folded = _fold(text)
    label_folded = _fold(label)
    idx = folded.find(label_folded)
    if idx < 0:
        return ""
    start = idx + len(label_folded)
    rest = text[start:].strip()
    # Stop at next major clause (period or " Tránh"/" Kỵ"/" Tốt cho")
    for stop in (".", " Tránh", " Kỵ", " Tốt cho", " tránh", " kỵ", " tốt cho"):
        stop_idx = rest.find(stop)
        if stop_idx > 0:
            rest = rest[:stop_idx]
            break
    return rest.strip()


def _keywords_match(segment: str, keywords: list[str]) -> bool:
    folded = _fold(segment)
    for kw in keywords:
        if _fold(kw) in folded:
            return True
    return False


def truc_verdict_for_activity(truc_info: dict, activity_slug: str) -> tuple[str, str, bool]:
    """Return (verdict, source, keyword_matched) for activity-specific Trực."""
    loi_khuyen = (truc_info.get("loi_khuyen") or "").strip()
    keywords = ACTIVITY_KEYWORDS.get(activity_slug, [])

    if loi_khuyen and keywords:
        tot_segment = _segment_after("Tốt cho", loi_khuyen)
        if tot_segment and _keywords_match(tot_segment, keywords):
            return _VERDICT_CAT, "truc_ngay", True

        for avoid_label in ("Tránh", "Kỵ"):
            avoid_segment = _segment_after(avoid_label, loi_khuyen)
            if avoid_segment and _keywords_match(avoid_segment, keywords):
                return _VERDICT_HUNG, "truc_ngay", True

    # Fallback: general Trực danh_gia (not activity-specific).
    return parse_danh_gia(truc_info.get("danh_gia")), "truc_ngay", False


def cat_hung_percent_general(
    ngay_hoang_dao: dict,
    truc_ngay: dict,
    nhi_thap_bat_tu: dict,
) -> int:
    """Legacy 50/25/25 formula (activity=all)."""
    ngay = parse_danh_gia(ngay_hoang_dao.get("danh_gia"))
    truc = parse_danh_gia(truc_ngay.get("danh_gia"))
    tu = parse_danh_gia(nhi_thap_bat_tu.get("danh_gia"))
    score = (
        _verdict_score(ngay) * 0.5
        + _verdict_score(truc) * 0.25
        + _verdict_score(tu) * 0.25
    )
    return int(round(max(0.0, min(100.0, score))))


def score_activity(
    truc_info: dict,
    ngay_hoang_dao: dict,
    xiu_info: dict,
    activity: str | None = None,
) -> dict:
    """Compute danh_gia_viec payload for a calendar day."""
    slug = normalize_activity(activity)

    if slug == ACTIVITY_ALL:
        per_activity = [
            score_activity(truc_info, ngay_hoang_dao, xiu_info, activity_slug)[
                "cat_percent"
            ]
            for activity_slug in ACTIVITY_SLUGS
            if activity_slug != ACTIVITY_ALL
        ]
        cat_percent = int(
            round(sum(per_activity) / len(per_activity))
        ) if per_activity else cat_hung_percent_general(
            ngay_hoang_dao, truc_info, xiu_info
        )
        if cat_percent >= 60:
            overall = _VERDICT_CAT
        elif cat_percent < 40:
            overall = _VERDICT_HUNG
        else:
            overall = _VERDICT_NEUTRAL
        return {
            "activity": ACTIVITY_ALL,
            "danh_gia": _DANH_GIA_LABEL[overall],
            "cat_percent": cat_percent,
            "nguon": "activity_average",
        }

    truc_v, nguon, truc_keyword = truc_verdict_for_activity(truc_info, slug)
    ngay_v = parse_danh_gia(ngay_hoang_dao.get("danh_gia"))
    tu_v = parse_danh_gia(xiu_info.get("danh_gia"))

    # Hắc Đạo: general Trực Cát does not override — only explicit lời khuyên match counts.
    if ngay_v == _VERDICT_HUNG and not truc_keyword:
        truc_v = _VERDICT_HUNG

    score = (
        _verdict_score(truc_v) * 0.5
        + _verdict_score(ngay_v) * 0.3
        + _verdict_score(tu_v) * 0.2
    )
    if ngay_v == _VERDICT_HUNG:
        score = min(score, 20.0)
    cat_percent = int(round(max(0.0, min(100.0, score))))

    if cat_percent >= 60:
        overall = _VERDICT_CAT
    elif cat_percent < 40:
        overall = _VERDICT_HUNG
    else:
        overall = _VERDICT_NEUTRAL

    return {
        "activity": slug,
        "danh_gia": _DANH_GIA_LABEL[overall],
        "cat_percent": cat_percent,
        "nguon": nguon,
    }


__all__ = [
    "cat_hung_percent_general",
    "parse_danh_gia",
    "score_activity",
    "truc_verdict_for_activity",
]
