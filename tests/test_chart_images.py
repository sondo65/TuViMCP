# -*- coding: utf-8 -*-
"""Tests for chart image base64 encoding helpers."""

from __future__ import annotations

import base64
import os
from pathlib import Path

from tuvi_mcp.api.chart_images import encode_png_base64


def test_encode_png_base64_from_bytes():
    raw = b"\x89PNG\r\n\x1a\n" + b"fake-png-bytes"
    encoded = encode_png_base64(raw)
    assert base64.b64decode(encoded) == raw


def test_encode_png_base64_from_path_deletes_source(tmp_path):
    path = tmp_path / "chart.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\nhello")
    encoded = encode_png_base64(str(path), delete_source=True)
    assert base64.b64decode(encoded) == b"\x89PNG\r\n\x1a\nhello"
    assert not path.exists()
