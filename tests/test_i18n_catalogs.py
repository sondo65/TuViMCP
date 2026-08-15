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


def test_t_empty_string_passthrough():
    assert t("en", "") == ""


def test_t_missing_key_falls_back_to_identity_not_blank():
    missing = "__not_a_catalog_key__"
    result = t("en", missing)
    assert result == missing
    assert result != ""
