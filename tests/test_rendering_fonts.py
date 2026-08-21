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


def test_locale_font_mapping():
    """Verify get_font maps locales to correct CJK font files."""
    # Test Chinese (Simplified) font
    font_zh = get_font(size=16, locale="zh")
    assert font_zh is not None
    assert isinstance(font_zh, ImageFont.FreeTypeFont)
    assert "NotoSerifSC" in os.path.basename(font_zh.path)
    
    # Test Japanese font
    font_ja = get_font(size=16, locale="ja")
    assert font_ja is not None
    assert isinstance(font_ja, ImageFont.FreeTypeFont)
    assert "NotoSerifJP" in os.path.basename(font_ja.path)
    
    # Test Korean font
    font_ko = get_font(size=16, locale="ko")
    assert font_ko is not None
    assert isinstance(font_ko, ImageFont.FreeTypeFont)
    assert "NotoSerifKR" in os.path.basename(font_ko.path)
    
    # Test Vietnamese/English/Malay use existing Noto Serif
    for locale in ["vi", "en", "ms"]:
        font = get_font(size=16, locale=locale)
        assert font is not None
        assert isinstance(font, ImageFont.FreeTypeFont)
        assert "NotoSerif-" in os.path.basename(font.path)
        assert font.path.endswith(".ttf")


def test_cjk_font_character_coverage():
    """Verify CJK fonts have proper character coverage for their target scripts."""
    # Test Chinese character coverage (命)
    font_zh = get_font(size=16, locale="zh")
    zh_mask = font_zh.getmask("命")
    assert zh_mask.size[0] > 0 and zh_mask.size[1] > 0
    
    # Test Korean Hangul coverage (명)
    font_ko = get_font(size=16, locale="ko") 
    ko_mask = font_ko.getmask("명")
    assert ko_mask.size[0] > 0 and ko_mask.size[1] > 0
    
    # Test Japanese character coverage (宮)
    font_ja = get_font(size=16, locale="ja")
    ja_mask = font_ja.getmask("宮")
    assert ja_mask.size[0] > 0 and ja_mask.size[1] > 0
    
    # Verify Vietnamese still works (ệ)
    font_vi = get_font(size=16, locale="vi")
    vi_mask = font_vi.getmask("ệ")
    assert vi_mask.size[0] > 0 and vi_mask.size[1] > 0


def test_six_locale_png_smoke():
    """Parametrized smoke test: all 6 locales produce valid PNG output."""
    from tuvi_mcp.horoscope import Horoscope
    import os
    
    test_locales = ["vi", "en", "zh", "ko", "ja", "ms"]
    
    for locale in test_locales:
        # Generate a chart for this locale
        h = Horoscope.from_birth(
            name="Test Name", day=15, month=8, year=1995, 
            hour=10, gender="Nam"
        )
        img_path = h.render_chart(year=2026, locale=locale)
        
        # Verify PNG is valid
        assert os.path.exists(img_path), f"PNG not created for locale {locale}"
        
        # Check file starts with PNG magic bytes
        with open(img_path, "rb") as f:
            magic = f.read(4)
            assert magic == b'\x89PNG', f"Invalid PNG magic for locale {locale}: {magic}"
        
        # Check reasonable file size (>50KB) 
        size = os.path.getsize(img_path)
        assert size > 50000, f"PNG too small for locale {locale}: {size} bytes"


def test_mixed_script_name_with_chinese_locale():
    """Mixed Vietnamese name on Chinese chart (font fallback test - D-23)."""
    from tuvi_mcp.horoscope import Horoscope
    import os
    
    # Vietnamese name with Chinese locale should still render
    h = Horoscope.from_birth(
        name="Nguyễn Văn A", day=20, month=5, year=1995,
        hour=11, gender="Nam" 
    )
    img_path = h.render_chart(year=2026, locale="zh")
    
    assert os.path.exists(img_path)
    size = os.path.getsize(img_path)
    assert size > 50000, f"Mixed name Chinese chart too small: {size} bytes"


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


def test_bagua_and_seal_have_no_square_card_frame():
    """Bagua compass and red Tử Vi seal drop the Stitch gold square card."""
    from tuvi_mcp._rendering import _load_asset

    _load_asset.cache_clear()
    for name in ("bagua.png", "seal_red.png"):
        im = _load_asset(name)
        assert im is not None
        w, h = im.size
        for x, y in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
            assert im.getpixel((x, y))[3] < 40, f"{name} corner {(x, y)} still opaque"
        top = sum(1 for x in range(w) if im.getpixel((x, 0))[3] > 80)
        assert top < w * 0.35, f"{name} still has a gold bar along the top"
        assert im.getpixel((w // 2, h // 2))[3] > 80


def test_draw_text_fallback_keeps_spaces_in_names():
    """Space glyphs have an empty mask; fallback drawing must still advance so họ/tên stay split."""
    from PIL import Image, ImageDraw

    from tuvi_mcp._rendering import draw_text_fallback, get_font, _px

    font = get_font(_px(28), True)

    def ink_width(text: str) -> int:
        im = Image.new("L", (1200, 120), 0)
        draw = ImageDraw.Draw(im)
        draw_text_fallback(draw, (10, 20), text, [font], fill=255)
        bbox = im.getbbox()
        return 0 if bbox is None else bbox[2] - bbox[0]

    spaced = ink_width("Nguyễn Văn An")
    glued = ink_width("NguyễnVănAn")
    assert spaced > glued + 10


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


def test_english_legend_stays_inside_gold_box():
    """English Temple/Prosper/Neutral must not spill past the gold legend frame."""
    from PIL import Image, ImageDraw

    from tuvi_mcp._rendering import STYLE, _legend_metrics, _legend_element_items, _legend_status_items, _px, _resolve_style, get_font

    s = _resolve_style(STYLE)
    ox = s.pad
    grid = s.cell * 4
    fy0 = ox + grid
    draw = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    font = get_font(_px(13), True)
    m = _legend_metrics(draw, font, ox, grid, fy0, s, _px(72), locale="en")
    x0, _y0, x1, _y1 = m["box"]
    pad = m["pad"]
    assert x1 <= ox + grid - _px(8) + 0.51
    items = _legend_status_items(draw, font, x0 + pad, locale="en", gap=m["status_gap"])
    last = items[-1]
    assert last[2] + last[3] <= x1 - pad + 0.51
    els = _legend_element_items(draw, font, x0 + pad, locale="en", gap=m["elem_gap"])
    last_el = els[-1]
    assert last_el[3] + last_el[4] <= x1 - pad + 0.51


def test_english_view_year_clears_red_seal():
    """EN View year value slides left of the seal without moving the whole column."""
    from tuvi_mcp._rendering import STYLE, _px, _resolve_style, _stamp_clear_xy

    s = _resolve_style(STYLE)
    ox = s.pad
    cx1 = ox + 3 * s.cell
    cy1 = ox + 3 * s.cell
    seal_sz, seal_m = _px(110), _px(14)
    seal_x = cx1 - seal_m - seal_sz
    seal_y = cy1 - seal_m - seal_sz
    rx, vx = 1451.0, 1662.0
    val_w = 100.0
    y = seal_y + _px(20)
    rx2, vx2 = _stamp_clear_xy(rx, vx, val_w, y, seal_x, seal_y, 800.0, 191.0, _px(10))
    assert vx2 + val_w <= seal_x - _px(8)
    # Rows above the seal keep their original x.
    rx3, vx3 = _stamp_clear_xy(rx, vx, val_w, seal_y - _px(80), seal_x, seal_y, 800.0, 191.0, _px(10))
    assert (rx3, vx3) == (rx, vx)


def test_vietnamese_thien_ban_columns_keep_gutter():
    """VI left values (15/5/1990) must not collide with right labels (Bản mệnh)."""
    from PIL import Image, ImageDraw

    from tuvi_mcp.horoscope import Horoscope
    from tuvi_mcp._rendering import (
        STYLE,
        _px,
        _resolve_style,
        _thien_ban_pack,
        get_font,
        t,
    )

    s = _resolve_style(STYLE)
    ox = s.pad
    cx0, cx1 = ox + s.cell, ox + 3 * s.cell
    draw = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    font_k = get_font(_px(20), False)
    font_v = get_font(_px(22), True)
    h = Horoscope.from_birth(
        name="Nguyễn Văn An", day=15, month=5, year=1990, hour=9, gender="Nam"
    )
    tb = h.chart().to_dict()["thien_ban"]
    left = [
        (t("vi", "Dương lịch", section="ui"), tb.get("ngay_duong", "")),
        (t("vi", "Âm lịch", section="ui"), tb.get("ngay_am", "")),
        (
            t("vi", "Giờ sinh", section="ui"),
            tb.get("gio_sinh")
            or f"{tb.get('can_gio_sinh', '')} {tb.get('chi_gio_sinh', '')}".strip(),
        ),
        (
            t("vi", "Năm sinh", section="ui"),
            f"{tb.get('can_nam', '')} {tb.get('chi_nam', '')}".strip(),
        ),
        (
            t("vi", "Âm dương", section="ui"),
            f"{tb.get('am_duong_nam_sinh', '')} {tb.get('gioi_tinh', '')}".strip(),
        ),
    ]
    right = [
        (t("vi", "Bản mệnh", section="ui"), t("vi", tb.get("ban_menh", "") or "", section="stars")),
        (
            t("vi", "Hành cục", section="ui"),
            f"{t('vi', tb.get('ten_cuc', '') or '', section='stars')} ({tb.get('hanh_cuc', '')})".strip(),
        ),
        (t("vi", "Chủ mệnh", section="ui"), t("vi", tb.get("menh_chu", "") or "", section="stars")),
        (t("vi", "Chủ thân", section="ui"), t("vi", tb.get("than_chu", "") or "", section="stars")),
        (t("vi", "Năm xem", section="ui"), "2024"),
    ]
    lab_gap = _px(10)
    left_x = cx0 + _px(18)
    left_lab_w = max(draw.textlength(k, font=font_k) for k, _ in left)
    left_val_w = max(draw.textlength(str(v), font=font_v) for _, v in left)
    right_lab_w = max(draw.textlength(k, font=font_k) for k, _ in right)
    right_val_w = max(draw.textlength(str(v), font=font_v) for _, v in right)
    left_end, right_x, gutter = _thien_ban_pack(
        left_x, left_lab_w, left_val_w, right_lab_w, right_val_w, lab_gap, cx1
    )
    assert right_x >= left_end + gutter
    # Packed against inner gold, not pulled left to the seal (that caused VI overlap).
    right_edge = cx1 - _px(16)
    packed = right_edge - (right_lab_w + lab_gap + right_val_w)
    assert abs(right_x - packed) < 0.51


def test_chu_than_stays_on_right_column_x():
    """Chủ thân must share the packed label x; only Năm xem may dodge the seal."""
    from PIL import Image

    from tuvi_mcp.horoscope import Horoscope
    from tuvi_mcp._rendering import STYLE, _px, _resolve_style

    s = _resolve_style(STYLE)
    ox = s.pad
    cy0, cy1 = ox + s.cell, ox + 3 * s.cell
    title_h, name_h, n_rows, row_h = _px(52), _px(34), 5, _px(50)
    data_h = n_rows * row_h
    ornament_h = max(_px(92), _px(124))
    blocks = title_h + ornament_h + _px(12) + name_h + data_h
    gap = max(_px(40), (cy1 - cy0) - blocks) / 4
    title_y = cy0 + gap
    icon_y = int(title_y + title_h + gap)
    name_y = int(icon_y + ornament_h + _px(12))
    data_y = int(name_y + name_h + gap)

    h = Horoscope.from_birth(
        name="Nguyễn Văn An", day=15, month=5, year=1990, hour=9, gender="Nam"
    )
    img_path = h.render_chart(year=2024)
    rgb = Image.open(img_path).convert("RGB")

    def is_ink(p):
        r, g, b = p
        return r < 130 and g < 120 and b < 110

    def right_label_x(row: int) -> int:
        y0 = data_y + row * row_h
        xs = []
        for y in range(y0 + 12, y0 + 55):
            for x in range(700, 1750):
                if is_ink(rgb.getpixel((x, y))):
                    xs.append(x)
        groups = []
        for x in sorted(set(xs)):
            if not groups or x - groups[-1][-1] > 20:
                groups.append([x])
            else:
                groups[-1].append(x)
        assert len(groups) >= 3, groups
        return groups[2][0]

    chu_than_x = right_label_x(3)
    assert abs(chu_than_x - right_label_x(0)) <= 8
    assert abs(chu_than_x - right_label_x(2)) <= 8
    assert abs(right_label_x(4) - right_label_x(0)) <= 8


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
