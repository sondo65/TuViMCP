# -*- coding: utf-8 -*-
"""Pixel-stability and paste-region compositing tests for lá số renderer."""

from __future__ import annotations

import hashlib
import os

import pytest
from PIL import Image, ImageChops, ImageDraw

from tuvi_mcp._rendering import _paste_rgba, _paste_rgba_outside
from tuvi_mcp.horoscope import Horoscope

# Golden RGB pixel hash for fixed birth chart (scale=2 traditional style).
# Update only when intentional visual changes are approved.
GOLDEN_CHART_RGB_SHA256 = (
    "b63bc65314b76d8b873e9fca4adcf34fd3147432f3dd34d95c79dff2988b1f1d"
)


def _full_canvas_paste_rgba(base: Image.Image, overlay: Image.Image, xy: tuple[int, int]) -> None:
    """Legacy full-canvas composite (pre-optimization reference)."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    layer.paste(overlay, xy, overlay)
    composited = Image.alpha_composite(base, layer)
    base.paste(composited)


def _full_canvas_paste_rgba_outside(
    base: Image.Image,
    overlay: Image.Image,
    xy: tuple[int, int],
    hole: tuple[int, int, int, int],
) -> None:
    """Legacy full-canvas outside paste (pre-optimization reference)."""
    from PIL import ImageChops as _Chops

    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    layer.paste(overlay, xy, overlay)
    mask = Image.new("L", base.size, 255)
    ImageDraw.Draw(mask).rectangle(hole, fill=0)
    r, g, b, a = layer.split()
    layer = Image.merge("RGBA", (r, g, b, _Chops.multiply(a, mask)))
    composited = Image.alpha_composite(base.convert("RGBA"), layer)
    base.paste(composited)


def test_paste_rgba_region_matches_full_canvas_composite():
    base_a = Image.new("RGBA", (200, 200), (251, 245, 233, 255))
    base_b = base_a.copy()
    overlay = Image.new("RGBA", (40, 40), (200, 50, 50, 180))
    ImageDraw.Draw(overlay).ellipse([4, 4, 35, 35], fill=(30, 120, 200, 220))

    _full_canvas_paste_rgba(base_a, overlay, (50, 60))
    _paste_rgba(base_b, overlay, (50, 60))

    assert base_a.tobytes() == base_b.tobytes(), "region paste must match full-canvas paste"


def test_paste_rgba_clips_when_overlay_extends_past_edge():
    base_a = Image.new("RGBA", (100, 100), (10, 20, 30, 255))
    base_b = base_a.copy()
    overlay = Image.new("RGBA", (40, 40), (255, 0, 0, 128))

    # Paste near bottom-right so overlay hangs past the canvas.
    _full_canvas_paste_rgba(base_a, overlay, (80, 80))
    _paste_rgba(base_b, overlay, (80, 80))

    assert base_a.tobytes() == base_b.tobytes()


def test_paste_rgba_outside_region_matches_full_canvas():
    base_a = Image.new("RGBA", (200, 200), (251, 245, 233, 255))
    base_b = base_a.copy()
    overlay = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rectangle([0, 0, 59, 59], fill=(201, 162, 39, 200))
    hole = (40, 40, 160, 160)

    _full_canvas_paste_rgba_outside(base_a, overlay, (10, 10), hole)
    _paste_rgba_outside(base_b, overlay, (10, 10), hole)

    assert base_a.tobytes() == base_b.tobytes()


def test_generate_laso_image_pixel_stable_golden():
    """Full chart RGB pixels must stay identical across renderer optimizations."""
    h = Horoscope.from_birth(
        name="Nguyễn Văn A",
        day=15,
        month=8,
        year=1995,
        hour=10,
        gender="Nam",
    )
    path = h.render_chart(year=2026, locale="vi")
    try:
        im = Image.open(path).convert("RGB")
        assert im.size == (2624, 2840)
        digest = hashlib.sha256(im.tobytes()).hexdigest()
        assert digest == GOLDEN_CHART_RGB_SHA256
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
