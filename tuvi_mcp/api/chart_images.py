# -*- coding: utf-8 -*-
"""Chart image helpers — encode rendered PNG for API responses (no disk persist)."""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Union


def encode_png_base64(
    source: Union[str, os.PathLike, bytes, bytearray],
    *,
    delete_source: bool = True,
) -> str:
    """Return base64 for PNG bytes or a rendered PNG path.

    :param source: Raw PNG bytes, or a filesystem path to a PNG
    :param delete_source: When ``source`` is a path and True, unlink after reading
    :return: Base64-encoded PNG bytes (no data-URI prefix)
    """
    if isinstance(source, (bytes, bytearray)):
        data = bytes(source)
    else:
        path = Path(source)
        data = path.read_bytes()
        if delete_source:
            try:
                os.unlink(path)
            except OSError:
                pass
    return base64.b64encode(data).decode("ascii")
