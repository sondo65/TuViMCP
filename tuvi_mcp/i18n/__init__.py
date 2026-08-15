# -*- coding: utf-8 -*-
"""Chart PNG vocabulary catalogs and locale lookup (D-18 / D-21)."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from importlib.resources import files

logger = logging.getLogger(__name__)

SUPPORTED_LOCALES = frozenset({"vi", "en", "zh", "ko", "ja", "ms"})
DEFAULT_LOCALE = "vi"

_PACKAGE = "tuvi_mcp.i18n"


def normalize_locale(raw: str | None) -> str:
    """Allowlist locale for POST generate (T-01-06-01 / T-01-06-03).

    None or blank → ``vi``. Strip + lower; raise ``ValueError`` if not allowlisted.
    Does not open files or treat ``raw`` as a path.
    """
    if raw is None:
        return DEFAULT_LOCALE
    code = str(raw).strip().lower()
    if code == "":
        return DEFAULT_LOCALE
    if code not in SUPPORTED_LOCALES:
        raise ValueError(f"unsupported locale: {raw!r}")
    return code


@lru_cache(maxsize=16)
def _load_catalog(locale: str) -> dict:
    """Load a packaged JSON catalog. ``locale`` must already be allowlisted."""
    safe = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
    root = files(_PACKAGE)
    resource = root.joinpath(f"{safe}.json")
    try:
        text = resource.read_text(encoding="utf-8")
    except (FileNotFoundError, OSError, ModuleNotFoundError):
        if safe != DEFAULT_LOCALE:
            return _load_catalog(DEFAULT_LOCALE)
        return {}
    loaded = json.loads(text)
    return loaded if isinstance(loaded, dict) else {}


def _lookup(catalog: dict, value: str, section: str | None) -> str | None:
    if section:
        mapping = catalog.get(section)
        if isinstance(mapping, dict) and value in mapping:
            found = mapping[value]
            return found if isinstance(found, str) else None
        return None
    for mapping in catalog.values():
        if isinstance(mapping, dict) and value in mapping:
            found = mapping[value]
            if isinstance(found, str):
                return found
    return None


def t(locale: str, value: str, *, section: str | None = None) -> str:
    """Translate a Vietnamese identity string for ``locale``.

    Empty string passthrough. Unknown/missing locale file behaves as ``vi``.
    Missing key falls back to Vietnamese identity, then the original value.
    """
    if not value:
        return value
    code = locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE
    found = _lookup(_load_catalog(code), value, section)
    if found is not None:
        return found
    if code != DEFAULT_LOCALE:
        vi_found = _lookup(_load_catalog(DEFAULT_LOCALE), value, section)
        if vi_found is not None:
            logger.debug("i18n miss locale=%s section=%s key=%r; using vi", locale, section, value)
            return vi_found
    logger.debug("i18n miss locale=%s section=%s key=%r; identity", locale, section, value)
    return value


__all__ = [
    "SUPPORTED_LOCALES",
    "DEFAULT_LOCALE",
    "normalize_locale",
    "t",
]
