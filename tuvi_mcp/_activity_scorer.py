# -*- coding: utf-8 -*-
"""Per-activity Cát/Hung scoring from auspicious day layers."""

from __future__ import annotations

import re
import unicodedata

from ._activity_catalog import (
    ACTIVITY_ALL,
    ACTIVITY_KEYWORDS,
    ACTIVITY_ORDER,
    ACTIVITY_SLUGS,
    normalize_activity,
)
from ._activity_rules import (
    DAY_CAP_RESOLVERS,
    DAY_CAP_TABOOS,
    HAC_DAO,
    HOANG_DAO,
    JI_NOTHING_GOOD,
    NGOC_HAP_KY,
    PHUC_DOAN_KY,
    PHUC_DOAN_XIU,
    TRUC_ACTIVITY_RULES,
    XIU_ACTIVITY_RULES,
    XIU_BRANCH_KY,
    XIU_BRANCH_VERDICT,
    expand_twins,
    slugs_for_yi_ji,
)

# Sources of a Nên / Kỵ verdict, in priority order for ``nguon``.
SOURCE_NGAY_KY = "ngay_ky"
SOURCE_NGAY_NGHI = "ngay_nghi"
SOURCE_TRUC = "truc"
SOURCE_TU = "tu"
SOURCE_NGOC_HAP = "ngoc_hap"

# Avoided activities never score above the "bad" tier (< 40).
AVOIDED_PERCENT_CAP = 30
# Weight of an avoided activity in the whole-day average: a day that only
# forbids some activities stays usable for the rest.
AVOIDED_DAY_WEIGHT = 0.5
# Whole-day ceiling on ``DAY_CAP_TABOOS`` days (neutral tier).
DAY_CAP_TABOO_PERCENT = 50
# Whole-day tier bounds; the by-month Hoàng / Hắc Đạo table picks the tier.
GOOD_DAY_PERCENT = 60
BAD_DAY_PERCENT = 40

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
    """Text after a label until the next sentence boundary marker.

    Matches the label with its accents as a whole word: folding would let
    "Kỵ" match inside "ký kết".
    """
    match = re.search(
        rf"(?<!\w){re.escape(label.lower())}(?!\w)",
        unicodedata.normalize("NFC", text).lower(),
    )
    if match is None:
        return ""
    rest = unicodedata.normalize("NFC", text)[match.end():].strip()
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


def _loi_khuyen_slugs(loi_khuyen: str) -> tuple[set[str], set[str]]:
    """(nên, kỵ) activity slugs mentioned in the two halves of ``loi_khuyen``."""
    nen: set[str] = set()
    ky: set[str] = set()
    if not loi_khuyen:
        return nen, ky
    tot_segment = _segment_after("Tốt cho", loi_khuyen)
    avoid_segments = [
        seg
        for seg in (_segment_after(label, loi_khuyen) for label in ("Tránh", "Kỵ"))
        if seg
    ]
    for slug, keywords in ACTIVITY_KEYWORDS.items():
        if tot_segment and _keywords_match(tot_segment, keywords):
            nen.add(slug)
        if any(_keywords_match(seg, keywords) for seg in avoid_segments):
            ky.add(slug)
    return nen, ky


def _strip_prefix(name: str, prefix: str) -> str:
    name = (name or "").strip()
    if name.lower().startswith(prefix.lower()):
        return name[len(prefix):].strip()
    return name


def xiu_verdict_for_day(xiu_info: dict, day_chi: str | None) -> str:
    """28 Tú verdict after the mansion's day-branch exceptions ("Ngoại lệ")."""
    xiu_name = _strip_prefix(xiu_info.get("ten", ""), "Sao")
    override = XIU_BRANCH_VERDICT.get(xiu_name, {}).get((day_chi or "").strip())
    return override or parse_danh_gia(xiu_info.get("danh_gia"))


def classify_day_activities(
    truc_info: dict,
    xiu_info: dict,
    yi: list[str] | None,
    ji: list[str] | None,
    day_chi: str | None = None,
    ngoc_hap: list[str] | None = None,
    cat_than: list[str] | None = None,
    hoang_dao_thang: str | None = None,
) -> dict:
    """Language-neutral Nên / Kỵ activity slugs for one day.

    Strict veto: an activity avoided by any source (day Kỵ list, Trực, Hung
    28 Tú, Ngọc Hạp taboo days) is avoided, even if another source recommends
    it. ``day_chi`` is the day's Earthly Branch (e.g. ``"Thân"``) for the 28 Tú
    exceptions; ``ngoc_hap`` lists the day's taboo names (keys of
    ``NGOC_HAP_KY``; unknown names are ignored); ``cat_than`` lists the day's
    auspicious stars, which can lift a taboo's whole-day ceiling;
    ``hoang_dao_thang`` is the by-month Hoàng / Hắc Đạo verdict
    (``hoang_dao_theo_thang``) that sets the whole-day tier.
    """
    yi = [item for item in (yi or []) if item]
    ji = [item for item in (ji or []) if item]
    day_chi = (day_chi or "").strip()
    truc_rule = TRUC_ACTIVITY_RULES.get(_strip_prefix(truc_info.get("ten", ""), "Trực"), {})
    xiu_name = _strip_prefix(xiu_info.get("ten", ""), "Sao")
    xiu_rule = XIU_ACTIVITY_RULES.get(xiu_name, {})
    xiu_verdict = xiu_verdict_for_day(xiu_info, day_chi)
    loi_nen, loi_ky = _loi_khuyen_slugs((truc_info.get("loi_khuyen") or "").strip())
    loi_ky = expand_twins(loi_ky)
    loi_nen = expand_twins(loi_nen) - loi_ky

    yi_slugs = slugs_for_yi_ji(yi)
    ky_sources: dict[str, list[str]] = {}

    def add_ky(slugs, source):
        for slug in slugs:
            sources = ky_sources.setdefault(slug, [])
            if source not in sources:
                sources.append(source)

    add_ky(slugs_for_yi_ji(ji), SOURCE_NGAY_KY)
    if JI_NOTHING_GOOD in ji:
        add_ky((s for s in ACTIVITY_ORDER if s not in yi_slugs), SOURCE_NGAY_KY)
    add_ky(truc_rule.get("ky", frozenset()) | loi_ky, SOURCE_TRUC)
    if xiu_verdict == _VERDICT_HUNG:
        add_ky(xiu_rule.get("ky", frozenset()), SOURCE_TU)
    add_ky(XIU_BRANCH_KY.get(xiu_name, {}).get(day_chi, frozenset()), SOURCE_TU)
    if day_chi and PHUC_DOAN_XIU.get(day_chi) == xiu_name:
        add_ky(PHUC_DOAN_KY, SOURCE_TU)
    for name in ngoc_hap or []:
        if name in NGOC_HAP_KY:
            add_ky(NGOC_HAP_KY[name] or ACTIVITY_ORDER, SOURCE_NGOC_HAP)

    nen_sources: dict[str, list[str]] = {}
    for slug in yi_slugs:
        nen_sources.setdefault(slug, []).append(SOURCE_NGAY_NGHI)
    for slug in truc_rule.get("nen", frozenset()) | loi_nen:
        nen_sources.setdefault(slug, []).append(SOURCE_TRUC)
    if xiu_verdict == _VERDICT_CAT:
        for slug in xiu_rule.get("nen", frozenset()):
            nen_sources.setdefault(slug, []).append(SOURCE_TU)

    return {
        "nen_lam": [
            slug for slug in ACTIVITY_ORDER if slug in nen_sources and slug not in ky_sources
        ],
        "nen_lam_nguon": {
            slug: nen_sources[slug]
            for slug in ACTIVITY_ORDER
            if slug in nen_sources and slug not in ky_sources
        },
        "can_tranh": [
            {"slug": slug, "nguon": ky_sources[slug]}
            for slug in ACTIVITY_ORDER
            if slug in ky_sources
        ],
        "tu_verdict": xiu_verdict,
        "ky_ca_ngay": [
            name
            for name in ngoc_hap or []
            if name in DAY_CAP_TABOOS
            and not DAY_CAP_RESOLVERS.get(name, frozenset()) & set(cat_than or [])
        ],
        "hoang_dao_thang": hoang_dao_thang,
    }


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
    *,
    yi: list[str] | None = None,
    ji: list[str] | None = None,
    classification: dict | None = None,
) -> dict:
    """Compute danh_gia_viec payload for a calendar day.

    ``yi`` / ``ji`` are the day's Nghi / Kỵ lists; pass ``classification`` from
    :func:`classify_day_activities` to avoid recomputing it per activity.
    """
    slug = normalize_activity(activity)
    if classification is None:
        classification = classify_day_activities(truc_info, xiu_info, yi, ji)

    if slug == ACTIVITY_ALL:
        avoided = {item["slug"] for item in classification["can_tranh"]}
        weighted = [
            (
                score_activity(
                    truc_info,
                    ngay_hoang_dao,
                    xiu_info,
                    activity_slug,
                    classification=classification,
                )["cat_percent"],
                AVOIDED_DAY_WEIGHT if activity_slug in avoided else 1.0,
            )
            for activity_slug in ACTIVITY_SLUGS
            if activity_slug != ACTIVITY_ALL
        ]
        cat_percent = int(
            round(sum(p * w for p, w in weighted) / sum(w for _, w in weighted))
        ) if weighted else cat_hung_percent_general(
            ngay_hoang_dao, truc_info, xiu_info
        )
        if classification.get("ky_ca_ngay"):
            cat_percent = min(cat_percent, DAY_CAP_TABOO_PERCENT)
        # Scores lifted into a higher tier keep a tenth of their spread so
        # days stay comparable within the tier.
        tier = classification.get("hoang_dao_thang")
        if tier == HOANG_DAO:
            if cat_percent < GOOD_DAY_PERCENT:
                cat_percent = GOOD_DAY_PERCENT + round(cat_percent * 0.1)
        elif tier == HAC_DAO:
            cat_percent = min(cat_percent, BAD_DAY_PERCENT - 1)
        elif cat_percent < BAD_DAY_PERCENT:
            cat_percent = BAD_DAY_PERCENT + round(cat_percent * 0.1)
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
    tu_v = classification.get("tu_verdict") or parse_danh_gia(xiu_info.get("danh_gia"))

    avoid_sources = next(
        (item["nguon"] for item in classification["can_tranh"] if item["slug"] == slug),
        None,
    )
    nen_sources = classification["nen_lam_nguon"].get(slug)
    if avoid_sources is None and nen_sources:
        # Recommended by the day's Nghi list or the Trực rules.
        truc_v, truc_keyword = _VERDICT_CAT, True
        if SOURCE_NGAY_NGHI in nen_sources:
            nguon = SOURCE_NGAY_NGHI

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
    if avoid_sources:
        score = min(score, float(AVOIDED_PERCENT_CAP))
        nguon = avoid_sources[0]
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
        "ly_do": list(avoid_sources or nen_sources or []),
    }


__all__ = [
    "AVOIDED_DAY_WEIGHT",
    "AVOIDED_PERCENT_CAP",
    "DAY_CAP_TABOO_PERCENT",
    "cat_hung_percent_general",
    "classify_day_activities",
    "parse_danh_gia",
    "score_activity",
    "truc_verdict_for_activity",
    "xiu_verdict_for_day",
]
