# -*- coding: utf-8 -*-
"""
(c) 2026 nmhaaa3218 <manh.ha.3218@gmail.com>

Traditional minh-họa lá số PNG renderer.
Visual contract aligned with Stitch traditional-laso reference
(`.stitch/designs/traditional-laso-stitch-reference.png`): navy/gold frame,
parchment cells, illustrated zodiac icons, center Bagua/dragons/seal,
footer zodiac strip + Âm lịch.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass, replace
from functools import lru_cache
from typing import Optional

from PIL import Image, ImageChops, ImageDraw, ImageFont

from tuvi_mcp.i18n import t


@dataclass(frozen=True)
class LasoStyle:
    parchment: str = "#FBF5E9"
    parchment_deep: str = "#F3E4C8"
    navy: str = "#1A2744"
    gold: str = "#C9A227"
    gold_bright: str = "#E0C35A"
    ink: str = "#1A1A1A"
    ink_muted: str = "#4A4035"
    title: str = "#1A2744"
    seal_red: str = "#B41E1E"
    menh_line: str = "#C98989"
    than_line: str = "#B5A47A"
    badge_fill: str = "#1A2744"
    badge_outline: str = "#C9A227"
    # Logical 1x geometry; PNG is emitted at `scale` using `_resolve_style`.
    pad: int = 36
    cell: int = 310
    footer: int = 108
    outer_w: int = 14
    grid_w: int = 2
    scale: int = 2


STYLE = LasoStyle()

ELEMENT_COLORS = {
    "Mộc": "#2E7D32",
    "Hỏa": "#C62828",
    "Thổ": "#B8860B",
    "Kim": "#5C6670",
    "Thủy": "#111111",
}

# cung_so 1..12 → grid (col, row); Tý bottom-center-right convention
CUNG_COORDS = {
    1: (2, 3),
    2: (1, 3),
    3: (0, 3),
    4: (0, 2),
    5: (0, 1),
    6: (0, 0),
    7: (1, 0),
    8: (2, 0),
    9: (3, 0),
    10: (3, 1),
    11: (3, 2),
    12: (3, 3),
}

TUAN_TRIET_PAIRS = ((1, 2), (3, 4), (5, 6), (7, 8), (9, 10), (11, 12))

# Fixed chi by cung_so (Địa bàn earth-branch positions)
CUNG_CHI = {
    1: "Tý",
    2: "Sửu",
    3: "Dần",
    4: "Mão",
    5: "Thìn",
    6: "Tỵ",
    7: "Ngọ",
    8: "Mùi",
    9: "Thân",
    10: "Dậu",
    11: "Tuất",
    12: "Hợi",
}

CHI_ASSET_KEYS = {
    "Tý": "ty",
    "Tí": "ty",
    "Sửu": "suu",
    "Dần": "dan",
    "Mão": "mao",
    "Mẹo": "mao",
    "Thìn": "thin",
    "Tỵ": "ti",
    "Tị": "ti",
    "Ngọ": "ngo",
    "Mùi": "mui",
    "Thân": "than",
    "Dậu": "dau",
    "Tuất": "tuat",
    "Hợi": "hoi",
}

CHI_ORDER = ["Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi"]

CHINH_TINH_IDS = set(range(1, 15))

TRANSIT_STAR_DETAILS = {
    "Lưu Thái Tuế": {"display": "L.Thái Tuế", "element": "H", "type": 15},
    "Lưu Lộc Tồn": {"display": "L.Lộc Tồn", "element": "O", "type": 3},
    "Lưu Kình Dương": {"display": "L.Kình Dương", "element": "K", "type": 11},
    "Lưu Đà La": {"display": "L.Đà La", "element": "K", "type": 11},
    "Lưu Thiên Mã": {"display": "L.Thiên Mã", "element": "H", "type": 3},
    "Lưu Thiên Khốc": {"display": "L.Thiên Khốc", "element": "T", "type": 12},
    "Lưu Thiên Hư": {"display": "L.Thiên Hư", "element": "T", "type": 12},
}

ATTR_SUFFIX_MAP = {
    "Miếu địa": "M",
    "Vượng địa": "V",
    "Đắc địa": "Đ",
    "Bình hòa": "B",
    "Hãm địa": "H",
}

TRANG_SINH_SET = {
    "Tràng sinh",
    "Mộc dục",
    "Quan đới",
    "Lâm quan",
    "Đế vượng",
    "Suy",
    "Bệnh",
    "Tử",
    "Mộ",
    "Tuyệt",
    "Thai",
    "Dưỡng",
}

_LATIN_CASE_LOCALES = frozenset({"vi", "en", "ms"})


def _display_case(locale: str, text: str) -> str:
    """Uppercase after lookup only for Latin script locales (never CJK)."""
    if locale in _LATIN_CASE_LOCALES:
        return text.upper()
    return text


def _t_tokens(locale: str, text: str, *sections: str) -> str:
    """Split whitespace, look up each token, rejoin."""
    if not text:
        return text
    out: list[str] = []
    for part in str(text).split():
        translated = part
        if sections:
            for sect in sections:
                candidate = t(locale, part, section=sect)
                if candidate != part:
                    translated = candidate
                    break
            else:
                translated = t(locale, part)
        else:
            translated = t(locale, part)
        out.append(translated)
    return " ".join(out)


def _px(n: float, scale: int | None = None) -> int:
    sc = STYLE.scale if scale is None else scale
    return int(round(n * sc))


def _font_ink_bottom(font, sample: str) -> int:
    try:
        return int(font.getbbox(sample)[3])
    except Exception:
        return _px(20)


def _palace_title_to_star_offset(font, palace: str) -> int:
    """Y offset from title_y to the first chính-tinh so Noto Serif diacritics don't collide."""
    ink = _font_ink_bottom(font, palace or "MỆNH")
    return ink + _px(6)


def _palace_stack_spacing(
    n_chinh: int,
    n_aux: int,
    usable: float,
    star_target: int,
    aux_target: int,
    gap_min: int,
    floor: int | None = None,
    extra_cap: int | None = None,
) -> tuple[float, float, float]:
    """Line heights for palace stars. Use leftover cell height instead of packing to _px(20)."""
    floor = _px(20) if floor is None else floor
    extra_cap = _px(10) if extra_cap is None else extra_cap
    n_chinh = max(0, int(n_chinh))
    n_aux = max(0, int(n_aux))
    gap = float(gap_min if n_chinh and n_aux else 0)
    slots = n_chinh + n_aux
    floors = n_chinh * floor + n_aux * floor + gap
    if slots == 0 or usable < floors:
        return float(floor), float(floor), gap
    target_need = n_chinh * star_target + n_aux * aux_target + gap
    if usable >= target_need:
        extra = min(usable - target_need, extra_cap * slots)
        bump = extra / slots
        return star_target + bump, aux_target + bump, gap
    bump = (usable - floors) / slots
    return floor + bump, floor + bump, gap


def _resolve_style(style: LasoStyle = STYLE) -> LasoStyle:
    """Physical canvas style: logical geometry × scale (sharper zoom)."""
    if style.scale <= 1:
        return style
    sc = style.scale
    return replace(
        style,
        pad=style.pad * sc,
        cell=style.cell * sc,
        footer=style.footer * sc,
        outer_w=style.outer_w * sc,
        grid_w=max(2, style.grid_w * sc),
        scale=1,
    )


def _canvas_size(style: LasoStyle = STYLE) -> tuple[int, int]:
    s = _resolve_style(style)
    grid = s.cell * 4
    w = s.pad * 2 + grid
    h = s.pad * 2 + grid + s.footer
    return w, h


def _assets_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "_assets", "laso")


@lru_cache(maxsize=128)
def _load_asset(filename: str) -> Optional[Image.Image]:
    path = os.path.join(_assets_dir(), filename)
    root = os.path.realpath(_assets_dir())
    real = os.path.realpath(path)
    if not real.startswith(root + os.sep) and real != root:
        return None
    if not os.path.isfile(real):
        return None
    try:
        im = Image.open(real).convert("RGBA")
    except Exception:
        return None
    if filename.startswith("stitch_"):
        return im
    if filename.startswith("corner_"):
        inset = max(4, int(round(min(im.size) * 0.09)))
        im = im.crop((inset, inset, im.size[0] - inset, im.size[1] - inset))
        im = _knockout_cream(im)
        im = _knockout_dark(im)
        bbox = im.getbbox()
        return im.crop(bbox) if bbox else im
    im = _knockout_cream(im)
    if filename.startswith("chi_"):
        im = _circular_medallion(im, drop_caption=True)
    elif filename in ("dragon_left.png", "dragon_right.png"):
        # Freeform S-dragons; circular mask shears whiskers/claws.
        im = _strip_square_frame(im)
        im = _knockout_cream(im, min_luma=165)
    elif filename in ("bagua.png", "seal_red.png"):
        im = _knockout_card_frame(im)
    return im


def _knockout_cream(im: Image.Image, min_luma: int = 198) -> Image.Image:
    """Flood-fill parchment/white from the tile edges so medallions/dragons keep only the art."""
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()

    def is_bg(x: int, y: int) -> bool:
        r, g, b, a = px[x, y]
        if a < 20:
            return True
        mn, mx = min(r, g, b), max(r, g, b)
        if mn >= min_luma:
            return True
        if mn >= min(170, min_luma - 10) and (mx - mn) < 78 and b >= 150:
            return True
        return False

    stack = []
    for x in range(w):
        stack.append((x, 0))
        stack.append((x, h - 1))
    for y in range(h):
        stack.append((0, y))
        stack.append((w - 1, y))

    seen = bytearray(w * h)
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h:
            continue
        idx = y * w + x
        if seen[idx]:
            continue
        seen[idx] = 1
        if not is_bg(x, y):
            continue
        px[x, y] = (0, 0, 0, 0)
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))

    # Second pass: punch remaining enclosed cream (inside gold rings)
    for y in range(h):
        for x in range(w):
            if is_bg(x, y):
                r, g, b, a = px[x, y]
                if a > 0:
                    px[x, y] = (r, g, b, 0)
    return im


def _knockout_dark(im: Image.Image) -> Image.Image:
    """Flood-fill navy/black card fill from the tile edges (Stitch corner plates)."""
    im = im.convert("RGBA")
    w, h = im.size
    px = im.load()

    def is_bg(x: int, y: int) -> bool:
        r, g, b, a = px[x, y]
        if a < 20:
            return True
        if max(r, g, b) < 70 and b >= r - 8:
            return True
        return False

    stack = []
    for x in range(w):
        stack.append((x, 0))
        stack.append((x, h - 1))
    for y in range(h):
        stack.append((0, y))
        stack.append((w - 1, y))

    seen = bytearray(w * h)
    while stack:
        x, y = stack.pop()
        if x < 0 or y < 0 or x >= w or y >= h:
            continue
        idx = y * w + x
        if seen[idx]:
            continue
        seen[idx] = 1
        if not is_bg(x, y):
            continue
        px[x, y] = (0, 0, 0, 0)
        stack.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    return im


def _knockout_card_frame(im: Image.Image, margin_frac: float = 0.08) -> Image.Image:
    """Punch the leftover Stitch gold square around bagua/seal; keep the inner art."""
    im = im.convert("RGBA")
    w, h = im.size
    if w < 8 or h < 8:
        return im
    px = im.load()
    margin = max(3, int(round(min(w, h) * margin_frac)))
    seen = bytearray(w * h)
    stack: list[tuple[int, int]] = []

    def push(x: int, y: int) -> None:
        if x < 0 or y < 0 or x >= w or y >= h:
            return
        idx = y * w + x
        if seen[idx] or px[x, y][3] < 20:
            return
        seen[idx] = 1
        stack.append((x, y))

    for y in range(h):
        for x in range(w):
            if x < margin or y < margin or x >= w - margin or y >= h - margin:
                push(x, y)
    i = 0
    while i < len(stack):
        x, y = stack[i]
        i += 1
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            push(x + dx, y + dy)
    if seen[(h // 2) * w + (w // 2)]:
        bbox = im.getbbox()
        return im.crop(bbox) if bbox else im
    for y in range(h):
        row = y * w
        for x in range(w):
            if seen[row + x]:
                px[x, y] = (0, 0, 0, 0)
    bbox = im.getbbox()
    return im.crop(bbox) if bbox else im


def _strip_square_frame(im: Image.Image) -> Image.Image:
    """Peel the Stitch gold square card frame; keep freeform dragon art."""
    im = im.convert("RGBA")
    w, h = im.size
    if w < 8 or h < 8:
        return im
    px = im.load()
    thresh = 40
    rows = [sum(1 for x in range(w) if px[x, y][3] > thresh) for y in range(h)]

    y0, y1 = 0, h
    while y0 < h and rows[y0] < max(4, w * 0.04):
        y0 += 1
    while y0 < h and rows[y0] >= w * 0.50:
        y0 += 1
    while y1 > y0 and rows[y1 - 1] < max(4, w * 0.04):
        y1 -= 1
    while y1 > y0 and rows[y1 - 1] >= w * 0.50:
        y1 -= 1
    if y1 - y0 < 8:
        bbox = im.getbbox()
        return im.crop(bbox) if bbox else im

    band = im.crop((0, y0, w, y1))
    bw, bh = band.size
    bpx = band.load()
    cols = [sum(1 for y in range(bh) if bpx[x, y][3] > thresh) for x in range(bw)]
    x0, x1 = 0, bw
    while x0 < bw and cols[x0] < max(4, bh * 0.04):
        x0 += 1
    while x0 < bw and cols[x0] >= bh * 0.50:
        x0 += 1
    while x1 > x0 and cols[x1 - 1] < max(4, bh * 0.04):
        x1 -= 1
    while x1 > x0 and cols[x1 - 1] >= bh * 0.50:
        x1 -= 1
    if x1 - x0 < 8:
        bbox = band.getbbox()
        return band.crop(bbox) if bbox else band

    inner = band.crop((x0, 0, x1, bh))
    bbox = inner.getbbox()
    if not bbox:
        return inner
    return inner.crop(bbox)


def _circular_medallion(im: Image.Image, drop_caption: bool = True) -> Image.Image:
    """Keep the full round badge: strip only the outer gold square and optional caption."""
    im = im.convert("RGBA")
    w, h = im.size
    if w < 8 or h < 8:
        return im
    px = im.load()
    thresh = 40
    rows = [sum(1 for x in range(w) if px[x, y][3] > thresh) for y in range(h)]

    y0, y1 = 0, h
    while y0 < h and rows[y0] >= w * 0.70:
        y0 += 1
    while y1 > y0 and rows[y1 - 1] >= w * 0.70:
        y1 -= 1
    while y0 < y1 and rows[y0] < max(8, w * 0.12):
        y0 += 1
    while y1 > y0 and rows[y1 - 1] < max(8, w * 0.12):
        y1 -= 1

    if drop_caption:
        gap_from = y0 + int((y1 - y0) * 0.55)
        for y in range(gap_from, y1):
            if rows[y] <= max(6, w // 16):
                y1 = y
                break

    if y1 - y0 < 8:
        bbox = im.getbbox()
        return im.crop(bbox) if bbox else im

    band = im.crop((0, y0, w, y1))
    bw, bh = band.size
    bpx = band.load()
    cols = [sum(1 for y in range(bh) if bpx[x, y][3] > thresh) for x in range(bw)]
    # Peel only the 1–6px gold-square edges, never the medallion body.
    x0, x1 = 0, bw
    for i in range(min(6, bw)):
        if cols[i] >= bh * 0.70 or cols[i] < max(4, bh * 0.08):
            x0 = i + 1
        else:
            break
    for i in range(bw - 1, max(bw - 7, x0), -1):
        if cols[i] >= bh * 0.70 or cols[i] < max(4, bh * 0.08):
            x1 = i
        else:
            break
    if x1 - x0 < 8:
        bbox = band.getbbox()
        return band.crop(bbox) if bbox else band

    inner = band.crop((x0, 0, x1, bh))
    tw, th = inner.size
    cx, cy = tw / 2.0, th / 2.0
    # Inscribed circle minus 0.5px so corners stay transparent; do not shrink the art.
    r = min(cx, cy) - 0.5
    if r < 8:
        bbox = inner.getbbox()
        return inner.crop(bbox) if bbox else inner
    mask = Image.new("L", inner.size, 0)
    ImageDraw.Draw(mask).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    alpha = ImageChops.multiply(inner.split()[-1], mask)
    inner.putalpha(alpha)
    trimmed = inner.getbbox()
    if not trimmed:
        return inner
    inner = inner.crop(trimmed)
    # Keep the gold ring off the bitmap edge so later scale/paste doesn't flatten it.
    pad = max(3, int(round(min(inner.size) * 0.06)))
    canvas = Image.new("RGBA", (inner.width + pad * 2, inner.height + pad * 2), (0, 0, 0, 0))
    canvas.paste(inner, (pad, pad), inner)
    return canvas


def _paste_rgba(base: Image.Image, overlay: Optional[Image.Image], xy: tuple[int, int]) -> None:
    if overlay is None:
        return
    if base.mode != "RGBA":
        base.paste(overlay, xy, overlay)
        return
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    layer.paste(overlay, xy, overlay)
    composited = Image.alpha_composite(base, layer)
    base.paste(composited)


def _fit_square(im: Image.Image, size: int, pad: int = 1) -> Image.Image:
    """Scale into a square canvas without stretching or re-clipping the badge."""
    inner = max(8, size - max(0, pad) * 2)
    fitted = im.copy()
    fitted.thumbnail((inner, inner), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ox = (size - fitted.width) // 2
    oy = (size - fitted.height) // 2
    canvas.paste(fitted, (ox, oy), fitted)
    return canvas


def _paste_rgba_outside(base: Image.Image, overlay: Optional[Image.Image], xy: tuple[int, int], hole: tuple[int, int, int, int]) -> None:
    """Paste overlay, clearing any pixels that would land inside ``hole`` (palace grid)."""
    if overlay is None:
        return
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    layer.paste(overlay, xy, overlay)
    mask = Image.new("L", base.size, 255)
    ImageDraw.Draw(mask).rectangle(hole, fill=0)
    r, g, b, a = layer.split()
    layer = Image.merge("RGBA", (r, g, b, ImageChops.multiply(a, mask)))
    composited = Image.alpha_composite(base.convert("RGBA"), layer)
    base.paste(composited)


def get_font(size=12, bold=False, font_path=None, locale="vi"):
    if font_path and isinstance(font_path, (str, os.PathLike)):
        try:
            if os.path.exists(font_path):
                return ImageFont.truetype(str(font_path), size)
        except Exception:
            pass

    # Map locales to font files (CJK vs Latin/Vietnamese)
    if locale in {"zh"}:
        font_filename = "NotoSerifSC-Bold.otf" if bold else "NotoSerifSC-Regular.otf"
    elif locale in {"ja"}:
        font_filename = "NotoSerifJP-Bold.otf" if bold else "NotoSerifJP-Regular.otf"
    elif locale in {"ko"}:
        font_filename = "NotoSerifKR-Bold.otf" if bold else "NotoSerifKR-Regular.otf"
    else:  # vi, en, ms and fallback
        font_filename = "NotoSerif-Bold.ttf" if bold else "NotoSerif-Regular.ttf"
    bundled_path = None
    try:
        from importlib.resources import files

        p = files("tuvi_mcp").joinpath("_fonts", font_filename)
        p_str = str(p)
        if os.path.exists(p_str):
            bundled_path = p_str
    except Exception:
        pass

    if not bundled_path or not os.path.exists(bundled_path):
        bundled_path = os.path.join(os.path.dirname(__file__), "_fonts", font_filename)

    try:
        if bundled_path and os.path.exists(bundled_path):
            return ImageFont.truetype(bundled_path, size)
    except Exception:
        pass

    # Prefer serif for traditional feel when available
    if bold:
        paths = [
            "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
            "/Library/Fonts/Times New Roman Bold.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "C:\\Windows\\Fonts\\timesbd.ttf",
        ]
    else:
        paths = [
            "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
            "/Library/Fonts/Times New Roman.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:\\Windows\\Fonts\\times.ttf",
        ]

    for p in paths:
        try:
            if os.path.exists(p):
                return ImageFont.truetype(p, size)
        except Exception:
            pass

    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        try:
            return ImageFont.load_default()
        except Exception:
            return None


def draw_text_fallback(draw, xy, text, fonts, fill, anchor=None):
    """
    Draw text using font fallback for mixed-script support.
    For each character, use the first font whose cmap can render it (not .notdef).
    
    Args:
        draw: PIL ImageDraw object
        xy: (x, y) position tuple
        text: text to draw
        fonts: list of PIL ImageFont objects in priority order
        fill: text color
        anchor: text anchor (optional)
    """
    if not text or not fonts:
        return
    
    x, y = xy
    
    for char in text:
        if char.isspace():
            font_sp = fonts[0]
            try:
                advance = font_sp.getlength(char)
            except Exception:
                advance = 0
            if advance <= 0:
                try:
                    advance = font_sp.getlength(" ")
                except Exception:
                    advance = _px(8)
            x += advance
            continue

        # Find the first font that can render this character
        font_to_use = None
        for font in fonts:
            try:
                # Check if font can render the character (has non-zero mask)
                mask = font.getmask(char)
                if mask.size[0] > 0 and mask.size[1] > 0:
                    # Additional check: ensure it's not a .notdef glyph by checking width
                    bbox = font.getbbox(char)
                    if bbox and bbox[2] > bbox[0]:  # has actual width
                        font_to_use = font
                        break
            except Exception:
                continue
        
        if font_to_use:
            # Draw this character with the selected font
            draw.text((x, y), char, fill=fill, font=font_to_use, anchor=anchor)
            
            # Advance x position for next character
            try:
                char_width = font_to_use.getlength(char)
                x += char_width
            except Exception:
                # Fallback to bbox width if getlength fails
                try:
                    bbox = font_to_use.getbbox(char)
                    x += (bbox[2] - bbox[0]) if bbox else 0
                except Exception:
                    x += 12  # Fallback fixed width


def _chi_key_for_cung(cung_so: int, cung_ten: str = "") -> str:
    chi = CUNG_CHI.get(cung_so, "")
    if not chi and cung_ten:
        parts = cung_ten.strip().split()
        chi = parts[-1] if parts else ""
    return CHI_ASSET_KEYS.get(chi, "")


def _chi_icon(cung_so: int, cung_ten: str = "", size: int = 36, gold: bool = False) -> Optional[Image.Image]:
    key = _chi_key_for_cung(cung_so, cung_ten)
    if not key:
        return None
    name = f"chi_gold_{key}.png" if gold else f"chi_{key}.png"
    icon = _load_asset(name)
    if icon is None and gold:
        icon = _load_asset(f"chi_{key}.png")
    if icon is None:
        return None
    return _fit_square(icon, size, pad=1)


def dich_cung(cung_start, offset):
    val = cung_start + offset
    if val % 12 == 0:
        return 12
    return val % 12


LEGEND_STATUSES = (("M", "Miếu"), ("V", "Vượng"), ("Đ", "Đắc"), ("B", "Bình"), ("H", "Hãm"))


def _legend_colon(draw, x, mid_y, color="#E0C35A", scale: int | None = None):
    """Two dots, taller than Noto Serif punctuation so M : Miếu stays readable."""
    sc = STYLE.scale if scale is None else scale
    r, gap = 1.4 * sc, 3.2 * sc
    for dy in (-gap, gap):
        draw.ellipse([x, mid_y + dy - r, x + 2 * r, mid_y + dy + r], fill=color)
    return x + _px(6, sc)


def _legend_status_items(draw, font, start_x=0.0, locale="vi"):
    """(abbrev, full, x, item_w) for M/V/Đ/B/H — same metrics as the footer paint loop."""
    sx = float(start_x)
    items = []
    for ab, full in LEGEND_STATUSES:
        ab_disp = t(locale, ab, section="brightness_abbrev")
        full_disp = t(locale, full, section="stars")
        ab_w = draw.textlength(ab_disp, font=font)
        colon_x = sx + ab_w + _px(3) + _px(6)
        item_w = colon_x + _px(3) - sx + draw.textlength(full_disp, font=font)
        items.append((ab_disp, full_disp, sx, item_w))
        sx += item_w + (_px(18) if ab == "V" else _px(14))
    return items


def _legend_status_content_width(draw, font, locale="vi") -> float:
    items = _legend_status_items(draw, font, locale=locale)
    _ab, _full, sx, item_w = items[-1]
    return sx + item_w - items[0][2]


def _legend_box(draw, font, ox, grid, fy0, style: LasoStyle, chi_stride: int, locale="vi"):
    """Gold legend rect sized so Hãm keeps inner padding; never overlap the Hợi chi tile."""
    content_w = _legend_status_content_width(draw, font, locale=locale)
    pad = _px(10)
    box_x1 = ox + grid - _px(8)
    box_x0 = int(round(box_x1 - pad * 2 - content_w))
    chi_right = ox + _px(8) + 11 * chi_stride + _px(62)
    box_x0 = max(box_x0, chi_right + _px(8))
    box_y0, box_y1 = fy0 + _px(8), fy0 + style.footer - _px(8)
    return box_x0, box_y0, box_x1, box_y1


def draw_badge(draw, cx, cy, text, w, h, font=None, style: LasoStyle = STYLE, locale="vi"):
    x0, y0, x1, y1 = cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2
    draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=_px(3),
        fill=style.badge_fill,
        outline=style.badge_outline,
        width=max(1, _px(1)),
    )
    if font is None:
        font = get_font(size=_px(9), bold=True, locale=locale)
    tw = draw.textlength(text, font=font)
    th = _px(10)
    try:
        bbox = font.getbbox(text)
        th = bbox[3] - bbox[1]
    except Exception:
        pass
    draw.text((cx - tw / 2, cy - th / 2 - _px(1)), text, fill="#FFFFFF", font=font)


def _tuan_triet_anchor(
    c1_id: int, c2_id: int, ox: int, oy: int, badge_w: int, badge_h: int, style: LasoStyle
) -> tuple[int, int, str]:
    """Park badges on the shared palace seam, at the midpoint between the pair — not the inner-gold T-junction."""
    col1, row1 = CUNG_COORDS[c1_id]
    col2, row2 = CUNG_COORDS[c2_id]
    cell = style.cell
    cy0, cy1 = oy + cell, oy + 3 * cell

    if row1 == row2:
        bx = ox + max(col1, col2) * cell
        if row1 == 0:
            return int(bx), int(cy0), "top"
        return int(bx), int(cy1), "center-bottom"
    if col1 == col2:
        # Midpoint of the two stacked palaces, not the ranh giới with thiên bàn.
        by = oy + max(row1, row2) * cell
        bx = ox + col1 * cell + cell // 2
        return int(bx), int(by), "left" if col1 == 0 else "right"
    return ox, oy, "none"


def _tuan_triet_seams(dia_ban) -> list[tuple[int, int]]:
    by_id = {c["cung_so"]: c for c in dia_ban}
    seams = []
    for a, b in TUAN_TRIET_PAIRS:
        c1, c2 = by_id.get(a), by_id.get(b)
        if not c1 or not c2:
            continue
        tuan = c1.get("tuan_trung") and c2.get("tuan_trung")
        triet = c1.get("triet_lo") and c2.get("triet_lo")
        if tuan or triet:
            seams.append((a, b))
    return seams


def _tuan_triet_badge_rects(
    dia_ban, ox: int, oy: int, badge_w: int, badge_h: int, style: LasoStyle
) -> list[tuple[float, float, float, float]]:
    rects = []
    hw, hh = badge_w / 2, badge_h / 2
    for a, b in _tuan_triet_seams(dia_ban):
        bx, by, _ = _tuan_triet_anchor(a, b, ox, oy, badge_w, badge_h, style)
        rects.append((bx - hw, by - hh, bx + hw, by + hh))
    return rects


def _cung_badge_insets(
    cung_so: int,
    rects,
    ox: int,
    oy: int,
    style: LasoStyle,
    pad_v: int | None = None,
) -> dict[str, int]:
    """Lift footer / drop header only on the palace edge the badge overlaps."""
    pad_v = _px(28) // 2 + _px(8) if pad_v is None else pad_v
    col, row = CUNG_COORDS[cung_so]
    cell = style.cell
    x0 = ox + col * cell
    y0 = oy + row * cell
    x1 = x0 + cell
    y1 = y0 + cell
    insets = {"top": 0, "bottom": 0, "left": 0, "right": 0}
    band = pad_v + _px(4)
    for bl, bt, br, bb in rects:
        if br <= x0 or bl >= x1 or bb <= y0 or bt >= y1:
            continue
        if bb > y0 and bt < y0 + band:
            insets["top"] = max(insets["top"], pad_v)
        if bt < y1 and bb > y1 - band:
            insets["bottom"] = max(insets["bottom"], pad_v)
    return insets


def draw_tuan_triet(draw, dia_ban, ox, oy, font_bold=None, style: LasoStyle = STYLE, locale="vi"):
    font = get_font(_px(16), True, locale=locale)
    badge_w, badge_h = _px(76), _px(28)
    cw, ch = _canvas_size(style)
    by_id = {c["cung_so"]: c for c in dia_ban}
    for c1_id, c2_id in TUAN_TRIET_PAIRS:
        c1, c2 = by_id.get(c1_id), by_id.get(c2_id)
        if not c1 or not c2:
            continue
        labels = []
        if c1.get("tuan_trung") and c2.get("tuan_trung"):
            labels.append(t(locale, "Tuần", section="ui"))
        if c1.get("triet_lo") and c2.get("triet_lo"):
            labels.append(t(locale, "Triệt", section="ui"))
        if not labels:
            continue
        bx, by, edge = _tuan_triet_anchor(c1_id, c2_id, ox, oy, badge_w, badge_h, style)
        for i, lab in enumerate(labels):
            cx, cy = bx, by
            if i:
                if edge in ("top", "center-bottom"):
                    cx += badge_w + _px(6)
                else:
                    cy += badge_h + _px(6)
            cx = max(badge_w // 2 + 1, min(cw - badge_w // 2 - 1, cx))
            cy = max(badge_h // 2 + 1, min(ch - badge_h // 2 - 1, cy))
            draw_badge(draw, cx, cy, lab, badge_w, badge_h, font=font, style=style, locale=locale)


def draw_lines_behind_center(draw, m_cung, t_cung, ox, oy, style: LasoStyle = STYLE):
    def get_center(cung_id):
        col, row = CUNG_COORDS[cung_id]
        return ox + col * style.cell + style.cell // 2, oy + row * style.cell + style.cell // 2

    if m_cung:
        p = get_center(m_cung)
        draw.line([p, get_center(dich_cung(m_cung, 4)), get_center(dich_cung(m_cung, 8)), p], fill=style.menh_line, width=2)
        draw.line([p, get_center(dich_cung(m_cung, 6))], fill=style.menh_line, width=2)
    if t_cung and t_cung != m_cung:
        p = get_center(t_cung)
        draw.line([p, get_center(dich_cung(t_cung, 4)), get_center(dich_cung(t_cung, 8)), p], fill=style.than_line, width=2)
        draw.line([p, get_center(dich_cung(t_cung, 6))], fill=style.than_line, width=2)


def generate_laso_image(
    chart_data: dict,
    current_year: int = None,
    font_path: str = None,
    font_bold_path: str = None,
    locale: str = "vi",
) -> str:
    """Render traditional square-ish lá số PNG (Stitch minh-họa style)."""
    style = _resolve_style(STYLE)
    thien_ban = chart_data.get("thien_ban", {})
    dia_ban = list(chart_data.get("dia_ban", []))

    m_cung = t_cung = None
    for cung in dia_ban:
        if cung.get("cung_chu") == "Mệnh":
            m_cung = cung["cung_so"]
        if cung.get("cung_than"):
            t_cung = cung["cung_so"]

    transit_stars = chart_data.get("transit_stars", [])
    if transit_stars:
        enriched = []
        for cung in dia_ban:
            cc = dict(cung)
            cc["sao"] = list(cung.get("sao", []))
            enriched.append(cc)
        for t_star in transit_stars:
            details = TRANSIT_STAR_DETAILS.get(t_star["name"])
            if not details:
                continue
            target = next((c for c in enriched if c["cung_so"] == t_star["cung_so"]), None)
            if target:
                target["sao"].append(
                    {
                        "id": 200,
                        "name": details["display"],
                        "element": details["element"],
                        "type": details["type"],
                        "yin_yang": 0,
                        "attribute": None,
                    }
                )
        dia_ban = enriched

    cw, ch = _canvas_size(style)
    parchment_rgb = (251, 245, 233)
    parchment_deep_rgb = (243, 228, 200)
    img = Image.new("RGBA", (cw, ch), (*parchment_deep_rgb, 255))
    draw = ImageDraw.Draw(img)

    ox = style.pad
    oy = style.pad
    grid = style.cell * 4

    # Full-chart eastern dragon watermark (behind grid + text)
    dragon_bg = _load_asset("dragon_bg.png")
    if dragon_bg is not None:
        dw = dragon_bg.resize((grid, grid), Image.Resampling.LANCZOS)
        r, g, b, a = dw.split()
        a = a.point(lambda v: int(v * 0.36))
        dw = Image.merge("RGBA", (r, g, b, a))
        _paste_rgba(img, dw, (ox, oy))

    # Outer navy frame + gold inner line
    draw.rectangle([0, 0, cw - 1, ch - 1], outline=style.navy, width=style.outer_w)
    inset = style.outer_w + 3
    draw.rectangle([inset, inset, cw - 1 - inset, ch - 1 - inset], outline=style.gold, width=_px(2))

    # Corner ornaments — L filigree clipped to the outer frame, never palace text
    corner_sz = _px(72)
    hole = (ox, oy, ox + grid, oy + grid)
    for key, xy in (
        ("tl", (1, 1)),
        ("tr", (cw - corner_sz - 1, 1)),
        ("bl", (1, ch - corner_sz - 1)),
        ("br", (cw - corner_sz - 1, ch - corner_sz - 1)),
    ):
        corner = _load_asset(f"corner_{key}.png")
        if corner:
            corner = corner.resize((corner_sz, corner_sz), Image.Resampling.LANCZOS)
            _paste_rgba_outside(img, corner, xy, hole)

    # Skip opaque cell fills so the dragon watermark shows through the grid.
    cx0, cy0 = ox + style.cell, oy + style.cell
    cx1, cy1 = ox + style.cell * 3, oy + style.cell * 3

    # Palace grid only — do not run navy lines through the merged center.
    for i in range(5):
        x = ox + i * style.cell
        y = oy + i * style.cell
        if i in (1, 2, 3):
            draw.line([(x, oy), (x, cy0)], fill=style.navy, width=style.grid_w)
            draw.line([(x, cy1), (x, oy + grid)], fill=style.navy, width=style.grid_w)
            draw.line([(ox, y), (cx0, y)], fill=style.navy, width=style.grid_w)
            draw.line([(cx1, y), (ox + grid, y)], fill=style.navy, width=style.grid_w)
        else:
            draw.line([(x, oy), (x, oy + grid)], fill=style.navy, width=style.grid_w)
            draw.line([(ox, y), (ox + grid, y)], fill=style.navy, width=style.grid_w)
    draw.rectangle([cx0, cy0, cx1, cy1], outline=style.gold, width=_px(3))

    bold_path = font_bold_path or font_path
    font_sm = get_font(_px(15), False, font_path, locale=locale)
    font_reg = get_font(_px(16), False, font_path, locale=locale)
    font_bold = get_font(_px(16), True, bold_path, locale=locale)
    font_palace = get_font(_px(22), True, bold_path, locale=locale)
    font_star = get_font(_px(18), True, bold_path, locale=locale)
    font_chi = get_font(_px(17), True, bold_path, locale=locale)
    badge_w, badge_h = _px(76), _px(28)
    badge_rects = _tuan_triet_badge_rects(dia_ban, ox, oy, badge_w, badge_h, style)
    badge_pad_v = badge_h // 2 + _px(8)

    # --- Palaces ---
    for cung in dia_ban:
        c_id = cung["cung_so"]
        col, row = CUNG_COORDS[c_id]
        x0 = ox + col * style.cell
        y0 = oy + row * style.cell
        x1 = x0 + style.cell
        y1 = y0 + style.cell
        ins = _cung_badge_insets(c_id, badge_rects, ox, oy, style, pad_v=badge_pad_v)
        top_pad, bot_pad = ins["top"], ins["bottom"]

        can_chi = cung.get("cung_ten", "")
        chi_name = CUNG_CHI.get(c_id, "")
        if " " in can_chi:
            can = can_chi.split(" ", 1)[0]
            can_abbr = t(locale, can, section="can_abbr") if can else ""
        else:
            can_abbr = ""

        hanh = cung.get("hanh_cung", "")
        dai_han = cung.get("dai_han")
        dai_str = str(dai_han) if dai_han is not None else ""
        month_idx = (c_id - 3) % 12 + 1

        # Header: index/chi first, circular medallion below, palace title last
        # (never overlay the red title — especially tight in the four corner cung)
        is_corner = (col in (0, 3) and row in (0, 3))
        icon_sz = _px(42) if is_corner else _px(48)
        idx_x = x0 + (_px(18) if is_corner and col == 0 else _px(6))
        chi_pad = _px(20) if is_corner and col == 3 else _px(8)
        hy0 = y0 + _px(4) + top_pad
        draw.text((idx_x, hy0), str(c_id), fill=style.ink_muted, font=font_sm)
        chi_label = _display_case(locale, f"{can_abbr}{t(locale, chi_name, section='chi') if chi_name else ''}")
        twc = draw.textlength(chi_label, font=font_chi)
        draw.text((x1 - chi_pad - twc, hy0), chi_label, fill=style.ink, font=font_chi)
        if dai_str:
            tw = draw.textlength(dai_str, font=font_bold)
            draw.text((x1 - chi_pad - tw, hy0 + _px(18)), dai_str, fill=style.ink_muted, font=font_bold)

        icon = _chi_icon(c_id, can_chi, size=icon_sz)
        icon_x = x0 + (style.cell - icon_sz) // 2
        icon_y = y0 + _px(10) + top_pad
        if is_corner:
            # Nudge toward the chart center, away from outer filigree / labels
            if col == 0:
                icon_x += _px(10)
            else:
                icon_x -= _px(10)
            if row == 0:
                icon_y += _px(4)
        if icon:
            _paste_rgba(img, icon, (icon_x, icon_y))

        palace_key = cung.get("cung_chu", "")
        palace = _display_case(locale, t(locale, palace_key, section="palaces") if palace_key else "")
        if cung.get("cung_than"):
            palace += t(locale, " · THÂN", section="ui")
        twp = draw.textlength(palace, font=font_palace)
        title_y = icon_y + icon_sz + (_px(10) if is_corner else _px(8))
        draw.text((x0 + style.cell / 2 - twp / 2, title_y), palace, fill=style.seal_red, font=font_palace)

        chinh, cat, sat = [], [], []
        trang = ""
        for s in cung.get("sao", []):
            name = s.get("name", "")
            if name in TRANG_SINH_SET:
                trang = t(locale, name, section="stars")
                continue
            el = {"M": "Mộc", "H": "Hỏa", "O": "Thổ", "K": "Kim", "T": "Thủy"}.get(s.get("element", ""), s.get("element", ""))
            color = ELEMENT_COLORS.get(el, style.ink)
            raw_attr = s.get("attribute", "") or ""
            attr = t(locale, raw_attr, section="brightness_abbrev") if raw_attr else ""
            if raw_attr and attr == raw_attr:
                attr = ATTR_SUFFIX_MAP.get(raw_attr, "")
            suffix = f" ({attr})" if attr else ""
            sid, stype = s.get("id"), s.get("type", 2)
            yy = s.get("yin_yang", 0)
            prefix = "+" if yy == 1 else "-" if yy == -1 else ""
            drawn_name = t(locale, name, section="stars") if name else ""
            if sid in CHINH_TINH_IDS:
                chinh.append((f"{prefix}{_display_case(locale, drawn_name)}{suffix}", color))
            elif stype < 10:
                cat.append((f"{drawn_name}{suffix}", color))
            else:
                sat.append((f"{drawn_name}{suffix}", color))

        # Stack: title → chính tinh → two auxiliary columns (serif needs real leading)
        n_chinh = min(2, len(chinh))
        n_aux = max(len(cat), len(sat))
        footer_y = y1 - _px(22) - bot_pad
        footer_limit = footer_y - _px(4)
        cy = title_y + _palace_title_to_star_offset(font_palace, palace)
        star_target = _font_ink_bottom(font_star, "THIÊN TƯỚNG (H)") + _px(6)
        aux_target = _font_ink_bottom(font_bold, "Kình dương") + _px(6)
        usable = footer_limit - cy
        star_lh, aux_lh, group_gap = _palace_stack_spacing(
            n_chinh, n_aux, usable, star_target, aux_target, gap_min=_px(8)
        )
        for nm, colr in chinh[:2]:
            tw = draw.textlength(nm, font=font_star)
            draw.text((x0 + style.cell / 2 - tw / 2, cy), nm, fill=colr, font=font_star)
            cy += star_lh

        aux_top = cy + group_gap
        y_left = aux_top
        for nm, colr in cat:
            if y_left + aux_lh > footer_limit:
                break
            draw.text((x0 + _px(8), y_left), nm, fill=colr, font=font_bold)
            y_left += aux_lh

        y_right = aux_top
        sat_x = x0 + style.cell // 2 + _px(6)
        for nm, colr in sat:
            if y_right + aux_lh > footer_limit:
                break
            draw.text((sat_x, y_right), nm, fill=colr, font=font_bold)
            y_right += aux_lh

        pattern = t(locale, "month_pattern", section="ui")
        try:
            thang = pattern.format(n=month_idx)
        except (KeyError, IndexError, ValueError):
            thang = pattern.replace("{n}", str(month_idx))
        draw.text((x0 + _px(8), footer_y), thang, fill=style.ink_muted, font=font_sm)
        if trang:
            tw = draw.textlength(trang, font=font_reg)
            draw.text((x0 + style.cell / 2 - tw / 2, footer_y), trang, fill=style.ink, font=font_reg)
        if hanh:
            hanh_disp = t(locale, hanh, section="elements")
            tw = draw.textlength(hanh_disp, font=font_sm)
            draw.text((x1 - _px(12) - tw, footer_y), hanh_disp, fill=style.ink_muted, font=font_sm)

    draw_tuan_triet(draw, dia_ban, ox, oy, font_bold=font_bold, style=style, locale=locale)

    # --- Center Thiên bàn: even vertical rhythm across the 2×2 square ---
    font_title = get_font(_px(48), True, bold_path, locale=locale)
    font_name = get_font(_px(28), True, bold_path, locale=locale)
    font_k = get_font(_px(20), False, font_path, locale=locale)
    font_v = get_font(_px(22), True, bold_path, locale=locale)

    title = _display_case(locale, t(locale, "LÁ SỐ TỬ VI", section="ui"))
    name_val = thien_ban.get("ten") or t(locale, "Khách", section="ui")
    title_h = _px(52)
    name_h = _px(34)
    n_rows = 5
    row_h = _px(50)
    data_h = n_rows * row_h
    dragon_sz = _px(92)
    bagua_sz = _px(124)
    ornament_h = max(dragon_sz, bagua_sz)
    icon_name_gap = _px(12)
    blocks = title_h + ornament_h + icon_name_gap + name_h + data_h
    # Equal pads around title / data; keep name tucked under the compass.
    free = max(_px(40), (cy1 - cy0) - blocks)
    gap = free / 4

    title_y = cy0 + gap
    icon_y = int(title_y + title_h + gap)
    name_y = int(icon_y + ornament_h + icon_name_gap)
    data_y = int(name_y + name_h + gap)

    tw = draw.textlength(title, font=font_title)
    draw.text((ox + grid / 2 - tw / 2, title_y), title, fill=style.title, font=font_title)

    bagua = _load_asset("bagua.png")
    if bagua:
        _paste_rgba(
            img,
            _fit_square(bagua, bagua_sz, pad=_px(1)),
            (ox + style.cell * 2 - bagua_sz // 2, icon_y),
        )

    dl = _load_asset("dragon_left.png")
    dr = _load_asset("dragon_right.png")
    dragon_y = icon_y + (ornament_h - dragon_sz) // 2
    if dl:
        _paste_rgba(img, _fit_square(dl, dragon_sz, pad=_px(4)), (cx0 + _px(18), dragon_y))
    if dr:
        _paste_rgba(img, _fit_square(dr, dragon_sz, pad=_px(4)), (cx1 - _px(18) - dragon_sz, dragon_y))

    # Use font fallback for mixed-script names (e.g. "Nguyễn" on Chinese chart)
    fallback_fonts = [font_name]  # Locale primary font first
    if locale in {"zh", "ja", "ko"}:
        # Add Latin/Vietnamese font as fallback for CJK locales
        fallback_fonts.append(get_font(_px(28), True, bold_path, locale="vi"))
    
    # Calculate width for centering (using primary font as approximation)
    tw = draw.textlength(name_val, font=font_name)
    draw_text_fallback(draw, (ox + grid / 2 - tw / 2, name_y), name_val, 
                      fallback_fonts, style.seal_red)

    ngay_duong = thien_ban.get("ngay_duong", "")
    ngay_am = thien_ban.get("ngay_am", "")
    gio_sinh = thien_ban.get("gio_sinh", "")
    can_gio = thien_ban.get("can_gio_sinh", "")
    chi_gio = thien_ban.get("chi_gio_sinh", "")
    gio_str = gio_sinh or f"{can_gio} {chi_gio}".strip()
    gio_str = _t_tokens(locale, gio_str, "can", "chi")
    nam_am = f"{thien_ban.get('can_nam', '')} {thien_ban.get('chi_nam', '')}".strip()
    nam_am = _t_tokens(locale, nam_am, "can", "chi")
    am_duong = f"{thien_ban.get('am_duong_nam_sinh', '')} {thien_ban.get('gioi_tinh', '')}".strip()
    am_duong = _t_tokens(locale, am_duong, "am_duong", "gender")
    ban_menh = t(locale, thien_ban.get("ban_menh", "") or "", section="stars")
    ten_cuc = t(locale, thien_ban.get("ten_cuc", "") or "", section="stars")
    cuc = f"{ten_cuc} ({thien_ban.get('hanh_cuc', '')})".strip()
    year_str = str(current_year) if current_year else t(locale, "N/A", section="ui")
    menh_chu = t(locale, thien_ban.get("menh_chu", "") or "", section="stars")
    than_chu = t(locale, thien_ban.get("than_chu", "") or "", section="stars")

    left = [
        (t(locale, "Dương lịch", section="ui"), ngay_duong),
        (t(locale, "Âm lịch", section="ui"), ngay_am),
        (t(locale, "Giờ sinh", section="ui"), gio_str),
        (t(locale, "Năm sinh", section="ui"), nam_am),
        (t(locale, "Âm dương", section="ui"), am_duong),
    ]
    right = [
        (t(locale, "Bản mệnh", section="ui"), ban_menh),
        (t(locale, "Hành cục", section="ui"), cuc),
        (t(locale, "Chủ mệnh", section="ui"), menh_chu),
        (t(locale, "Chủ thân", section="ui"), than_chu),
        (t(locale, "Năm xem", section="ui"), year_str),
    ]

    left_x = cx0 + _px(18)
    right_edge = cx1 - _px(16)
    lab_gap = _px(10)
    left_lab_w = max(draw.textlength(k, font=font_k) for k, _ in left)
    right_lab_w = max(draw.textlength(k, font=font_k) for k, _ in right)
    left_val_w = max((draw.textlength(str(v), font=font_v) for _, v in left), default=0)
    right_val_w = max((draw.textlength(str(v), font=font_v) for _, v in right), default=0)
    # Pack right column against the inner gold so long values (Hành cục) stay inside
    right_block = right_lab_w + lab_gap + right_val_w
    right_x = right_edge - right_block
    left_end = left_x + left_lab_w + lab_gap + left_val_w
    gutter = _px(16)
    if right_x < left_end + gutter:
        right_x = left_end + gutter
    ly = data_y
    for k, v in left:
        draw.text((left_x, ly), k, fill=style.ink_muted, font=font_k)
        draw.text((left_x + left_lab_w + lab_gap, ly), str(v), fill=style.ink, font=font_v)
        ly += row_h

    ry = data_y
    for k, v in right:
        draw.text((right_x, ry), k, fill=style.ink_muted, font=font_k)
        draw.text((right_x + right_lab_w + lab_gap, ry), str(v), fill=style.ink, font=font_v)
        ry += row_h

    seal_sz = _px(110)
    seal_m = _px(14)
    seal = _load_asset("seal_red.png")
    if seal:
        _paste_rgba(
            img,
            _fit_square(seal, seal_sz, pad=_px(2)),
            (cx1 - seal_m - seal_sz, cy1 - seal_m - seal_sz),
        )
    else:
        draw.rectangle(
            [cx1 - seal_m - seal_sz, cy1 - seal_m - seal_sz, cx1 - seal_m, cy1 - seal_m],
            outline=style.seal_red,
            width=_px(2),
        )

    # --- Footer ---
    fy0 = oy + grid
    draw.rectangle([ox, fy0, ox + grid, fy0 + style.footer], fill=style.navy)
    draw.line([(ox, fy0), (ox + grid, fy0)], fill=style.gold, width=_px(2))

    font_ft = get_font(_px(13), True, bold_path, locale=locale)
    chi_stride = _px(72)
    for i, chi in enumerate(CHI_ORDER):
        key = CHI_ASSET_KEYS[chi]
        tile = _load_asset(f"chi_{key}.png")
        ix = ox + _px(8) + i * chi_stride
        if tile:
            tile = _fit_square(tile, _px(62), pad=_px(3))
            _paste_rgba(img, tile, (ix, fy0 + _px(8)))
        chi_disp = _display_case(locale, t(locale, chi, section="chi"))
        tw = draw.textlength(chi_disp, font=font_ft)
        draw.text((ix + _px(31) - tw / 2, fy0 + _px(74)), chi_disp, fill=style.gold_bright, font=font_ft)

    # Legend: ngũ hành colors + Miếu/Vượng/Đắc/Bình/Hãm (box grows with Noto Serif)
    font_leg = get_font(_px(13), True, bold_path, locale=locale)
    box_x0, box_y0, box_x1, box_y1 = _legend_box(draw, font_leg, ox, grid, fy0, style, chi_stride, locale=locale)
    draw.rectangle([box_x0, box_y0, box_x1, box_y1], outline=style.gold, width=max(1, _px(1)))
    elements = [
        ("Kim", ELEMENT_COLORS["Kim"]),
        ("Mộc", ELEMENT_COLORS["Mộc"]),
        ("Thủy", ELEMENT_COLORS["Thủy"]),
        ("Hỏa", ELEMENT_COLORS["Hỏa"]),
        ("Thổ", ELEMENT_COLORS["Thổ"]),
    ]
    ex, ey = box_x0 + _px(10), box_y0 + _px(14)
    cap = draw.textbbox((0, 0), "H", font=font_leg)
    cap_mid = (cap[1] + cap[3]) / 2
    chip = _px(10)
    for name, colr in elements:
        cy = ey + cap_mid - _px(1)
        draw.rounded_rectangle(
            [ex, cy - chip / 2, ex + chip, cy + chip / 2],
            radius=max(1, _px(1)),
            fill=colr,
            outline="#F5E6C8",
            width=max(1, _px(1)),
        )
        draw.text((ex + chip + _px(5), ey), t(locale, name, section="elements"), fill="#F5E6C8", font=font_leg)
        ex += _px(64)
    sy = box_y0 + _px(50)
    for ab, full, sx, _item_w in _legend_status_items(draw, font_leg, box_x0 + _px(10), locale=locale):
        draw.text((sx, sy), ab, fill=style.gold_bright, font=font_leg)
        ab_w = draw.textlength(ab, font=font_leg)
        colon_x = _legend_colon(draw, sx + ab_w + _px(3), sy + cap_mid, style.gold_bright)
        draw.text((colon_x + _px(3), sy), full, fill="#F5E6C8", font=font_leg)

    safe = str(name_val).replace(" ", "_")
    out = os.path.join(tempfile.gettempdir(), f"tuvi_chart_{safe}.png")
    flat = Image.new("RGBA", img.size, (*parchment_deep_rgb, 255))
    Image.alpha_composite(flat, img).convert("RGB").save(
        out, "PNG", dpi=(144, 144), compress_level=4
    )
    return out
