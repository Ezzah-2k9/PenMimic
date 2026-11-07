"""
render.py - draw a Layout onto paper using Pillow.

Each glyph is stored as an ink-strength mask. To draw it we scale and tilt the mask, then paste a
block of the chosen ink colour through it. That makes recolouring free.
"""

import math

from PIL import Image, ImageColor

PAPER_STYLES = ("plain", "lined")
PAPER_COLOR = (255, 255, 255)
LINE_COLOR = (176, 198, 232)


def parse_color(ink):
    try:
        return ImageColor.getrgb(ink)[:3]
    except ValueError:
        raise ValueError(f"Unknown colour {ink!r}. Use a name like 'navy' or a hex code like '#1b1b3a'.") from None


def blank_paper(layout, style):
    if style not in PAPER_STYLES:
        raise ValueError(f"paper must be one of {PAPER_STYLES}, not {style!r}")
    canvas = Image.new("RGB", (layout.width, layout.height), PAPER_COLOR)
    if style == "lined":
        y = layout.first_baseline + 6                    # writing sits just above each line
        while y < layout.height - 20:
            canvas.paste(LINE_COLOR, (0, round(y), layout.width, round(y) + 2))
            y += layout.pitch
    return canvas


def draw_placement(canvas, placement, ink_rgb):
    glyph, scale = placement.glyph, placement.scale
    source = glyph.alpha
    if placement.trim_left or placement.trim_right:
        source = source.crop((placement.trim_left, 0, glyph.width - placement.trim_right, glyph.height))
    w, h = max(1, round(source.width * scale)), max(1, round(source.height * scale))
    mask = source.resize((w, h), Image.LANCZOS)
    if abs(placement.angle) > 0.01:
        mask = mask.rotate(placement.angle, resample=Image.BICUBIC, expand=True)

    centre_x = placement.x + w / 2
    top = placement.baseline_y - glyph.baseline * scale   # align the glyph's baseline to the line
    centre_y = top + h / 2
    position = (round(centre_x - mask.width / 2), round(centre_y - mask.height / 2))
    canvas.paste(Image.new("RGB", mask.size, ink_rgb), position, mask)


def render_image(layout, ink="#1b1b3a", paper="plain"):
    canvas = blank_paper(layout, paper)
    rgb = parse_color(ink)
    for placement in layout.placements:
        draw_placement(canvas, placement, rgb)
    return canvas


def render_frames(layout, ink="#1b1b3a", paper="plain", max_frames=60):
    """Frames for the 'writing' animation: the page starts blank, glyphs appear left to right."""
    canvas = blank_paper(layout, paper)
    rgb = parse_color(ink)
    frames = [canvas.copy()]
    total = len(layout.placements)
    step = max(1, math.ceil(total / max_frames))
    for i, placement in enumerate(layout.placements, start=1):   # already in reading order
        draw_placement(canvas, placement, rgb)
        if i % step == 0 or i == total:
            frames.append(canvas.copy())
    return frames