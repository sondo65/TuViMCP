# -*- coding: utf-8 -*-
"""
Tests for bundled font loading and custom font_path override in tuvi_mcp._rendering.
"""
import os
from unittest.mock import patch
from PIL import ImageFont
import pytest

from tuvi_mcp._rendering import get_font, generate_laso_image
from tuvi_mcp.horoscope import Horoscope


def test_bundled_font_resolution():
    """Verify that get_font resolves bundled Noto Serif fonts."""
    font_reg = get_font(size=12, bold=False)
    assert font_reg is not None
    assert isinstance(font_reg, ImageFont.FreeTypeFont)
    assert "NotoSerif-Regular" in os.path.basename(font_reg.path)

    font_bold = get_font(size=14, bold=True)
    assert font_bold is not None
    assert isinstance(font_bold, ImageFont.FreeTypeFont)
    assert "NotoSerif-Bold" in os.path.basename(font_bold.path)

    glyphs = font_reg.getmask("Hành cục ệỉửơđấở")
    assert glyphs.size[0] > 0 and glyphs.size[1] > 0


def test_headless_environment_fallback():
    """Simulate a headless environment with no OS desktop fonts installed."""
    orig_exists = os.path.exists

    def fake_exists(path):
        # Return False for all OS system font paths, but True for bundled Noto Serif fonts
        if "Arial" in str(path) or "/usr/share/fonts" in str(path) or "Windows\\Fonts" in str(path):
            return False
        return orig_exists(path)

    with patch("os.path.exists", side_effect=fake_exists):
        font = get_font(size=12, bold=False)
        assert font is not None
        assert isinstance(font, ImageFont.FreeTypeFont)


def test_custom_font_path_override():
    """Verify custom font_path parameter overrides defaults."""
    bundled_path = os.path.join(os.path.dirname(__file__), "..", "tuvi_mcp", "_fonts", "NotoSerif-Regular.ttf")
    assert os.path.exists(bundled_path)
    font = get_font(size=16, font_path=bundled_path)
    assert font is not None
    assert isinstance(font, ImageFont.FreeTypeFont)


def test_generate_laso_image_renders_with_bundled_font(tmp_path):
    """Test generating a chart PNG image using Horoscope API."""
    h = Horoscope.from_birth(name="Nguyễn Văn A", day=15, month=8, year=1995, hour=10, gender="Nam")
    img_path = h.render_chart(year=2026)

    assert os.path.exists(img_path)
    assert os.path.getsize(img_path) > 0
    assert img_path.endswith(".png")


def test_invalid_font_path_graceful_fallback():
    """Verify non-existent or invalid font_path falls back gracefully to bundled font."""
    font = get_font(size=12, font_path="/path/to/non_existent_font.ttf")
    assert font is not None
    assert isinstance(font, ImageFont.FreeTypeFont)


def test_corrupted_font_file_fallback(tmp_path):
    """Verify corrupted TTF file falls back gracefully without raising an unhandled exception."""
    bad_font_file = tmp_path / "broken.ttf"
    bad_font_file.write_text("This is not a font file.")

    font = get_font(size=12, font_path=str(bad_font_file))
    assert font is not None


def test_invalid_type_font_path():
    """Verify passing non-string invalid types (int, dict, list) to font_path is handled safely."""
    font1 = get_font(size=12, font_path=12345)
    assert font1 is not None

    font2 = get_font(size=12, font_path={"invalid": "object"})
    assert font2 is not None


def test_complete_absence_of_fonts_fallback():
    """Verify load_default fallback when both OS fonts and bundled fonts are simulated missing."""
    with patch("os.path.exists", return_value=False):
        font = get_font(size=12)
        assert font is not None


def test_render_chart_long_vietnamese_name_and_transit():
    """Test rendering chart with long Vietnamese diacritic name and transit stars."""
    h = Horoscope.from_birth(
        name="Nguyễn Hoàng Quốc Phượng Cửu Trọng Thiên",
        day=29,
        month=12,
        year=1999,
        hour=23,
        gender="Nữ",
    )
    img_path = h.render_chart(year=2026)
    assert os.path.exists(img_path)
    assert os.path.getsize(img_path) > 0


def test_traditional_palette_smoke():
    """Rendered PNG uses traditional navy/parchment palette (not modern gray grid)."""
    from PIL import Image

    from tuvi_mcp._rendering import ELEMENT_COLORS, STYLE, _canvas_size, _resolve_style

    assert ELEMENT_COLORS["Mộc"] != "#059669"
    assert ELEMENT_COLORS["Thủy"] != "#2563EB"
    assert STYLE.navy == "#1A2744"

    h = Horoscope.from_birth(
        name="Nguyễn Văn An",
        day=15,
        month=5,
        year=1990,
        hour=9,
        gender="Nam",
    )
    img_path = h.render_chart(year=2024)
    assert os.path.exists(img_path)
    assert os.path.getsize(img_path) > 50_000

    with Image.open(img_path) as im:
        expected_w, expected_h = _canvas_size()
        assert im.size == (expected_w, expected_h)
        rgb = im.convert("RGB")

        # Navy outer frame along left edge (mid-height; skip gold corner tiles)
        border_px = rgb.getpixel((1, expected_h // 2))
        assert border_px[0] < 40 and border_px[2] > 50

        s = _resolve_style(STYLE)
        pad, cell = s.pad, s.cell
        center_px = rgb.getpixel((pad + cell + cell // 2, pad + cell + 160 * STYLE.scale))
        assert center_px[0] > 180 and center_px[1] > 170
        assert center_px != (255, 255, 255)

        # Below chi names, away from corner filigree and the legend box
        footer_px = rgb.getpixel((pad + 200 * STYLE.scale, pad + 4 * cell + s.footer - 12 * STYLE.scale))
        assert footer_px[0] < 80 and footer_px[2] >= footer_px[0]


def test_chi_icon_is_circular_without_square_frame():
    """Zodiac tiles crop to the round medallion; square gold card frame is gone."""
    from tuvi_mcp._rendering import _chi_icon, _load_asset

    _load_asset.cache_clear()
    icon = _chi_icon(7, "Nhâm Ngọ", size=40)
    assert icon is not None
    assert icon.size == (40, 40)
    px = icon.load()
    for x, y in ((0, 0), (39, 0), (0, 39), (39, 39)):
        assert px[x, y][3] < 40, f"corner {(x, y)} still opaque: {px[x, y]}"
    assert px[20, 20][3] > 80
    loaded = _load_asset("chi_ngo.png")
    assert loaded is not None
    # Occupancy crop must keep the full ~104px medallion, not a 80px shaved disk.
    assert loaded.size[0] >= 95 and loaded.size[1] >= 95
    bbox = loaded.getbbox()
    assert bbox is not None
    assert bbox[2] - bbox[0] >= 90 and bbox[3] - bbox[1] >= 90


def test_center_dragons_have_no_square_card_frame():
    """Center dragon tiles drop the Stitch gold square; corners stay transparent."""
    from tuvi_mcp._rendering import _load_asset

    _load_asset.cache_clear()
    for name in ("dragon_left.png", "dragon_right.png"):
        im = _load_asset(name)
        assert im is not None
        w, h = im.size
        for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
            assert im.getpixel((x, y))[3] < 40, f"{name} corner {(x, y)} still opaque"
        top = sum(1 for x in range(w) if im.getpixel((x, 0))[3] > 80)
        assert top < w * 0.25, f"{name} still has a gold bar along the top"


def test_legend_ham_has_right_padding():
    """Footer legend Hãm stays inside the gold box with inner padding (Noto Serif)."""
    from PIL import Image, ImageDraw

    from tuvi_mcp._rendering import (
        STYLE,
        _legend_box,
        _legend_status_content_width,
        _px,
        _resolve_style,
        get_font,
    )

    s = _resolve_style(STYLE)
    ox = s.pad
    grid = s.cell * 4
    fy0 = ox + grid
    draw = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    font = get_font(_px(13), True)
    x0, _y0, x1, _y1 = _legend_box(draw, font, ox, grid, fy0, s, _px(72))
    content_w = _legend_status_content_width(draw, font)
    pad = _px(10)
    assert x0 + pad + content_w <= x1 - pad + 0.51
    chi_right = ox + _px(8) + 11 * _px(72) + _px(62)
    assert x0 >= chi_right + _px(6)


def test_palace_title_to_star_clears_serif_ink():
    """Noto Serif palace titles (PHỤ MẪU) sit above the first star, not overlapping it."""
    from tuvi_mcp._rendering import _palace_title_to_star_offset, _px, get_font

    font = get_font(_px(22), True)
    offset = _palace_title_to_star_offset(font, "PHỤ MẪU")
    ink_bottom = font.getbbox("PHỤ MẪU")[3]
    assert offset >= ink_bottom + _px(6)


def test_palace_stack_spacing_looser_when_cell_has_room():
    """Sparse palaces use leftover cell height as extra leading instead of dumping it at the footer."""
    from tuvi_mcp._rendering import _palace_stack_spacing, _px

    floor = _px(20)
    star_t, aux_t = 56, 52
    star_lh, aux_lh, gap = _palace_stack_spacing(
        n_chinh=1, n_aux=4, usable=328, star_target=star_t, aux_target=aux_t, gap_min=_px(6)
    )
    assert star_lh > floor
    assert aux_lh > floor
    assert star_lh >= star_t
    assert aux_lh >= aux_t
    assert 1 * star_lh + gap + 4 * aux_lh <= 328 + 0.51


def test_palace_stack_spacing_keeps_floor_when_crowded():
    from tuvi_mcp._rendering import _palace_stack_spacing, _px

    floor = _px(20)
    star_lh, aux_lh, _gap = _palace_stack_spacing(
        n_chinh=2, n_aux=7, usable=328, star_target=56, aux_target=52, gap_min=_px(6)
    )
    assert star_lh >= floor
    assert aux_lh >= floor


def test_triet_anchor_ngo_mui():
    """Can Ất/Canh: Triệt sits on the inner gold T-junction of Ngọ–Mùi."""
    from tuvi_mcp._rendering import STYLE, _px, _resolve_style, _tuan_triet_anchor

    s = _resolve_style(STYLE)
    ox = oy = s.pad
    cy0 = oy + s.cell
    x, y, edge = _tuan_triet_anchor(7, 8, ox, oy, _px(76), _px(28), s)
    assert edge == "top"
    ngo_mui_seam = ox + 2 * s.cell
    assert abs(x - ngo_mui_seam) <= _px(4)
    assert abs(y - cy0) <= _px(4)


def test_tuan_anchor_than_dau():
    """Ất Hợi / Giáp Tuất tuần: Tuần sits at the midpoint of Thân–Dậu, not the inner-gold ranh giới."""
    from tuvi_mcp._rendering import STYLE, _px, _resolve_style, _tuan_triet_anchor

    s = _resolve_style(STYLE)
    ox = oy = s.pad
    bw, bh = _px(76), _px(28)
    x, y, edge = _tuan_triet_anchor(9, 10, ox, oy, bw, bh, s)
    cx1, cy0 = ox + 3 * s.cell, oy + s.cell
    mid_x = cx1 + s.cell // 2
    assert edge == "right"
    assert abs(x - mid_x) <= _px(4)
    assert abs(y - cy0) <= _px(8)
    ngo_mui_x = ox + 2 * s.cell
    assert abs(x - ngo_mui_x) > s.cell // 3


def test_at_hoi_chart_flags_tuan_than_dau_triet_ngo_mui():
    """Year stem/branch only: Ất Hợi → Triệt Ngọ–Mùi, Tuần Thân–Dậu. Hour Tuất does not move them."""
    from tuvi_mcp.horoscope import Horoscope

    h = Horoscope.from_birth(
        name="Đỗ Trường Sơn", day=20, month=5, year=1995, hour=11, gender="Nam"
    )
    chart = h.chart().to_dict()
    by_id = {c["cung_so"]: c for c in chart["dia_ban"]}
    assert chart["thien_ban"]["can_nam"] == "Ất"
    assert chart["thien_ban"]["chi_nam"] == "Hợi"
    for i in (7, 8):
        assert by_id[i]["triet_lo"] is True
        assert by_id[i]["tuan_trung"] is False
    for i in (9, 10):
        assert by_id[i]["tuan_trung"] is True
        assert by_id[i]["triet_lo"] is False


def test_cung_badge_insets_lift_text_off_inner_gold():
    """Footer/header on the gold T-junction yield to Tuần/Triệt; other cung stay put."""
    from tuvi_mcp.horoscope import Horoscope
    from tuvi_mcp._rendering import (
        STYLE,
        _cung_badge_insets,
        _px,
        _resolve_style,
        _tuan_triet_badge_rects,
    )

    h = Horoscope.from_birth(
        name="Nguyễn Văn An", day=15, month=5, year=1990, hour=9, gender="Nam"
    )
    dia = h.chart().to_dict()["dia_ban"]
    s = _resolve_style(STYLE)
    ox = oy = s.pad
    bw, bh = _px(76), _px(28)
    rects = _tuan_triet_badge_rects(dia, ox, oy, bw, bh, s)
    pad_v = bh // 2 + _px(8)

    ngo = _cung_badge_insets(7, rects, ox, oy, s, pad_v=pad_v)
    mui = _cung_badge_insets(8, rects, ox, oy, s, pad_v=pad_v)
    assert ngo["bottom"] >= pad_v
    assert mui["bottom"] >= pad_v
    assert ngo["top"] == 0
    assert mui["top"] == 0

    tuat = _cung_badge_insets(11, rects, ox, oy, s, pad_v=pad_v)
    hoi = _cung_badge_insets(12, rects, ox, oy, s, pad_v=pad_v)
    ty = _cung_badge_insets(1, rects, ox, oy, s, pad_v=pad_v)
    assert tuat["bottom"] >= pad_v
    assert hoi["top"] >= pad_v
    assert ty["top"] == 0

    thin = _cung_badge_insets(5, rects, ox, oy, s, pad_v=pad_v)
    assert thin == {"top": 0, "bottom": 0, "left": 0, "right": 0}
