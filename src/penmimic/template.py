"""Printable Penmimic template sheets: preserved block and guided cursive styles.

Geometry intentionally matches the supplied project dump's glyph extractor. Keep this
module's constants aligned with src/penmimic/glyphs.py when integrating it there.
"""
from __future__ import annotations
from pathlib import Path
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont

STYLES = ("block", "cursive")
UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
LOWER = "abcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"
PUNCTUATION = ".,!?'\"-:;()"
CHARACTERS = UPPER + LOWER + DIGITS + PUNCTUATION
VARIANTS = 5
PAGE_W, PAGE_H = 2480, 3508
MARKER_SIZE = 100
MARKER_CENTERS = [(150, 150), (PAGE_W-150, 150), (PAGE_W-150, PAGE_H-150), (150, PAGE_H-150)]
ROWS_PER_PAGE = 15
CELL_W, CELL_H = 360, 190
LABEL_W = 220
GRID_TOP = 400
GRID_LEFT = (PAGE_W - (LABEL_W + VARIANTS * CELL_W)) // 2
BASELINE_FRACTION = 0.68
XHEIGHT_FRACTION = 0.43
PAGE_COUNT = -(-len(CHARACTERS) // ROWS_PER_PAGE)
PAGE_DOT, PAGE_DOT_STEP, PAGE_DOT_ORIGIN = 40, 70, (300, 250)
PAGE_NUMBER_REGION = (280, 240, 280 + PAGE_DOT_STEP * 8, 300)
STYLE_BAR = (1700, 250, 1900, 290)
STYLE_REGION = (1600, 240, 2200, 300)
GUIDE_GRAY = 205
JOIN_DOT_OFFSET = 82

DARK = 42
MUTED = 100
PALE = 214


def cell_box(row: int, variant: int) -> Tuple[int, int, int, int]:
    x0 = GRID_LEFT + LABEL_W + variant * CELL_W
    y0 = GRID_TOP + row * CELL_H
    return x0, y0, x0 + CELL_W, y0 + CELL_H


def baseline_y(row: int) -> int:
    return GRID_TOP + row * CELL_H + int(CELL_H * BASELINE_FRACTION)


def xheight_y(row: int) -> int:
    return GRID_TOP + row * CELL_H + int(CELL_H * XHEIGHT_FRACTION)


def page_characters(page: int) -> str:
    if not 1 <= page <= PAGE_COUNT:
        raise ValueError(f"page must be between 1 and {PAGE_COUNT}")
    start = (page - 1) * ROWS_PER_PAGE
    return CHARACTERS[start:start + ROWS_PER_PAGE]


def is_joined_row(style: str, char: str) -> bool:
    return style == "cursive" and char.isascii() and char.islower()


def _font(size: int, bold: bool = False):
    candidates = (["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if bold else []) + [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            pass
    return ImageFont.load_default()


def render_template_page(page: int, style: str = "block") -> Image.Image:
    if style not in STYLES:
        raise ValueError(f"style must be one of {STYLES}, not {style!r}")
    chars = page_characters(page)
    img = Image.new("L", (PAGE_W, PAGE_H), 255)
    draw = ImageDraw.Draw(img)
    for cx, cy in MARKER_CENTERS:
        half = MARKER_SIZE // 2
        draw.rectangle((cx-half, cy-half, cx+half, cy+half), fill=0)

    title = "BLOCK LETTERS" if style == "block" else "CURSIVE LETTERS"
    draw.text((300, 112), title, font=_font(54, True), fill=DARK)
    draw.text((300, 182), f"PENMIMIC  /  TEMPLATE {page} OF {PAGE_COUNT}", font=_font(27, True), fill=MUTED)
    for i in range(page):
        x = PAGE_DOT_ORIGIN[0] + i * PAGE_DOT_STEP
        draw.rectangle((x, PAGE_DOT_ORIGIN[1], x+PAGE_DOT, PAGE_DOT_ORIGIN[1]+PAGE_DOT), fill=0)
    if style == "cursive":
        draw.rectangle(STYLE_BAR, fill=0)

    if style == "block":
        instructions = ["Write one separate character in each box. Keep it upright and sit it on the dotted baseline.",
                        "Use a dark pen; leave all five samples in a row distinct. Keep ink inside the box."]
    else:
        instructions = ["a-z: write one cursive letter in each box with a short entry and exit stroke at the dots. A-Z, 0-9: write them in your cursive style.",
                        "Use only short entry/exit strokes near the dots; do not draw a long line across the box. Follow x-height and baseline."]
    for i, text in enumerate(instructions):
        draw.text((300, 318 + i*38), text, font=_font(27), fill=MUTED)

    for row, char in enumerate(chars):
        top = GRID_TOP + row * CELL_H
        # Row label and group cue
        draw.text((GRID_LEFT + 24, top + CELL_H//2), char, font=_font(76, True), fill=DARK, anchor="mm")
        group = "a-z" if char.islower() else ("A-Z" if char.isupper() else "0-9" if char.isdigit() else "MARK")
        draw.text((GRID_LEFT + 24, top + CELL_H//2 + 53), group, font=_font(17, True), fill=MUTED, anchor="mm")
        by = baseline_y(row)
        xy = xheight_y(row)
        for variant in range(VARIANTS):
            x0, y0, x1, y1 = cell_box(row, variant)
            draw.rectangle((x0, y0, x1, y1), outline=GUIDE_GRAY, width=3)
            # dotted baseline; lower-case cursive ascenders reach above x-height guide.
            for x in range(x0+12, x1-10, 26):
                draw.line((x, by, x+12, by), fill=GUIDE_GRAY, width=3)
            if style == "cursive" and char.islower():
                # A light, solid x-height guide: descenders (g,j,p,q,y) naturally cross below baseline.
                draw.line((x0+8, xy, x1-8, xy), fill=PALE, width=2)
                lx, rx, r = x0+JOIN_DOT_OFFSET, x1-JOIN_DOT_OFFSET, 10
                draw.ellipse((lx-r, by-r, lx+r, by+r), fill=112)
                draw.ellipse((rx-r, by-r, rx+r, by+r), outline=112, width=3)
    return img


def render_template_pages(style: str = "block") -> List[Image.Image]:
    if style not in STYLES:
        raise ValueError(f"style must be one of {STYLES}, not {style!r}")
    return [render_template_page(p, style) for p in range(1, PAGE_COUNT+1)]


def make_template(path: str | Path = "template.pdf", style: str = "block") -> Path:
    pages = render_template_pages(style)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    pages[0].save(target, "PDF", save_all=True, append_images=pages[1:], resolution=300.0)
    return target


def make_both_templates(output_dir: str | Path = ".") -> tuple[Path, Path]:
    out = Path(output_dir)
    return (make_template(out / "penmimic_block_template.pdf", "block"),
            make_template(out / "penmimic_cursive_template.pdf", "cursive"))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate printable block and cursive practice sheets.")
    parser.add_argument("--output-dir", default=".", help="folder for the generated PDFs")
    args = parser.parse_args()
    for output in make_both_templates(args.output_dir):
        print(f"Created {output.resolve()}")


