# -*- coding: utf-8 -*-
"""Chart image helpers — encode rendered PNG for API responses (no disk persist)."""

from __future__ import annotations

import base64
import os
from pathlib import Path


def encode_png_base64(source_path: str, *, delete_source: bool = True) -> str:
    """Read a rendered PNG, return base64, and optionally delete the source file.

    :param source_path: Path to the rendered PNG (typically system temp)
    :param delete_source: When True, unlink source after reading (best-effort)
    :return: Base64-encoded PNG bytes (no data-URI prefix)
    :raises: OSError / FileNotFoundError if the file cannot be read
    """
    path = Path(source_path)
    data = path.read_bytes()
    if delete_source:
        try:
            os.unlink(path)
        except OSError:
            pass
    return base64.b64encode(data).decode("ascii")
