# -*- coding: utf-8 -*-
"""Catalog completeness and t() contracts for chart i18n (D-21)."""

from __future__ import annotations

import json
from importlib.resources import files

from tuvi_mcp.i18n import SUPPORTED_LOCALES, t

OTHER_LOCALES = ("en", "zh", "ko", "ja", "ms")


def _leaf_paths(obj: object, prefix: tuple[str, ...] = ()) -> set[tuple[str, ...]]:
    """Collect nested dict paths to every non-dict leaf."""
    paths: set[tuple[str, ...]] = set()
    if not isinstance(obj, dict):
        return paths
    for key, value in obj.items():
        path = prefix + (str(key),)
        if isinstance(value, dict):
            paths.update(_leaf_paths(value, path))
        else:
            paths.add(path)
    return paths


def _load_catalog(locale: str) -> dict:
    text = files("tuvi_mcp.i18n").joinpath(f"{locale}.json").read_text(encoding="utf-8")
    loaded = json.loads(text)
    assert isinstance(loaded, dict)
    return loaded


def test_supported_locales_allowlist():
    assert SUPPORTED_LOCALES == frozenset({"vi", "en", "zh", "ko", "ja", "ms"})


def test_catalog_leaf_keys_present_in_all_locales():
    vi_leaves = _leaf_paths(_load_catalog("vi"))
    assert vi_leaves
    for locale in OTHER_LOCALES:
        missing = vi_leaves - _leaf_paths(_load_catalog(locale))
        assert not missing, f"{locale}.json missing leaf keys: {sorted(missing)[:20]}"


def test_t_vi_identity():
    assert t("vi", "Tử vi") == "Tử vi"
    assert t("vi", "Mệnh", section="palaces") == "Mệnh"


def test_t_en_title_is_translated():
    assert t("en", "LÁ SỐ TỬ VI", section="ui") != "LÁ SỐ TỬ VI"


def test_en_catalog_uses_english_not_pinyin():
    """Palace and major-star labels are English words, not Hanyu pinyin."""
    assert t("en", "Mệnh", section="palaces") == "Life"
    assert t("en", "Tử vi", section="stars") == "Emperor"
    assert t("en", "Thiên cơ", section="stars") == "Advisor"
    assert t("en", "Miếu", section="stars") == "Temple"
    assert t("en", "Tý", section="chi") == "Rat"
    assert t("en", "Chủ mệnh", section="ui") == "Life star"


def test_t_empty_string_passthrough():
    assert t("en", "") == ""


def test_t_missing_key_falls_back_to_identity_not_blank():
    missing = "__not_a_catalog_key__"
    result = t("en", missing)
    assert result == missing
    assert result != ""


def test_cjk_translations_not_identity_stubs():
    """zh/ko/ja/ms catalogs have real translations, not Vietnamese identity."""
    # Test that key UI elements are actually translated  
    test_cases = [
        ("ja", "LÁ SỐ TỬ VI", "ui"),
        ("zh", "LÁ SỐ TỬ VI", "ui"), 
        ("ko", "LÁ SỐ TỬ VI", "ui"),
        ("ms", "LÁ SỐ TỬ VI", "ui"),
        ("zh", "Mệnh", "palaces"),
        ("ja", "Mệnh", "palaces"),
        ("ko", "Mệnh", "palaces"),
        ("ms", "Mệnh", "palaces"),
        ("ja", "Tử vi", "stars"),
        ("ja", "Dương lịch", "ui"),
        ("ja", "Phụ mẫu", "palaces"),
        ("ja", "Giáp", "can"),
        ("ja", "Tý", "chi"),
        ("zh", "Tử vi", "stars"),
        ("zh", "Dương lịch", "ui"),
        ("zh", "Nam", "gender"),
        ("ko", "Tử vi", "stars"),
        ("ko", "Dương lịch", "ui"),
        ("ko", "Nam", "gender"),
        ("ko", "Phụ mẫu", "palaces"),
        ("ko", "Giáp", "can"),
        ("ms", "Tử vi", "stars"),
        ("ms", "Dương lịch", "ui"),
        ("ms", "Nam", "gender"),
        ("ms", "Phụ mẫu", "palaces"),
        ("ms", "Giáp", "can"),
    ]

    for locale, key, section in test_cases:
        translated = t(locale, key, section=section)
        assert translated != key, f"Locale '{locale}' key '{key}' in section '{section}' is untranslated: {translated}"


_ALLOWED_IDENTITY_SECTIONS = {"brightness_abbrev"}
_ALLOWED_IDENTITY_KEYS = {("ui", "N/A")}


def test_translated_catalogs_are_not_vietnamese_identity():
    """en/zh/ko/ja/ms values must not copy vi.json except compact tokens."""
    vi_catalog = _load_catalog("vi")
    for locale in OTHER_LOCALES:
        catalog = _load_catalog(locale)
        stubs: list[str] = []
        for section, mapping in vi_catalog.items():
            if not isinstance(mapping, dict):
                continue
            for key, value in mapping.items():
                if section in _ALLOWED_IDENTITY_SECTIONS or (section, key) in _ALLOWED_IDENTITY_KEYS:
                    continue
                if catalog[section][key] == value:
                    stubs.append(f"{locale}.{section}.{key}")
        assert not stubs, f"{locale} still has Vietnamese identity stubs: {stubs[:20]}"
