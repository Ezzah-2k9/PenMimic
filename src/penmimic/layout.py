"""
layout.py - decide WHERE every character goes. No drawing happens here, so it is easy to test.

For each character we pick a random handwritten variant, then add small random changes
("jitter") to size, tilt, baseline height and spacing, so the result does not look copy-pasted.
Words are wrapped onto new lines when they would cross the right margin.
"""

import math
import random
import statistics
from dataclasses import dataclass

from .glyphs import Glyph

# Typographic characters people paste from word processors -> the plain ones we have samples for
SUBSTITUTIONS = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2013": "-", "\u2014": "-", "\u2026": ".",
}


@dataclass(frozen=True)
class LayoutOptions:
    size: float = 1.0           # 1.0 = as written on the template (300 dpi)
    line_spacing: float = 1.6   # distance between baselines, as a multiple of a typical letter height
    jitter: float = 1.0         # 0 = every letter identical in size/tilt; 1 = natural; 2 = messy
    width: int = 1600           # page width in pixels
    margin: int = 80
    style: str = "block"
    letter_spacing: float = 1.0 # multiplier: <1 tighter, >1 looser (cursive: >1 opens the joins)
    word_spacing: float = 1.0   # multiplier for the space between words


@dataclass
class Placement:
    glyph: Glyph
    x: float                    # left edge of the glyph
    baseline_y: float           # y of the writing baseline for this glyph (includes wobble)
    scale: float
    angle: float                # degrees, counter-clockwise
    trim_left: int = 0          # glyph pixels cropped off the left (cursive word-start tail)
    trim_right: int = 0         # glyph pixels cropped off the right (cursive word-end tail)


@dataclass
class Layout:
    placements: list
    width: int
    height: int
    pitch: float                # distance between lines
    first_baseline: float
    n_lines: int


def reference_height(glyphs):
    """A typical letter height, used to scale spacing. Median of the a-z glyph heights."""
    letters = [g.height for c, gs in glyphs.items() if c.islower() and c.isascii() for g in gs]
    everything = [g.height for gs in glyphs.values() for g in gs]
    values = letters or everything
    if not values:
        raise ValueError("No glyphs available to lay out text.")
    return statistics.median(values)


def _lookup(glyphs, char):
    """Variants for `char`, with fallbacks: swapped case, then '?', else None (leave a gap)."""
    char = SUBSTITUTIONS.get(char, char)
    for candidate in (char, char.swapcase(), "?"):
        if glyphs.get(candidate):
            return glyphs[candidate]
    return None


def layout_text(text, glyphs, options, rng):
    unit = reference_height(glyphs)
    size = options.size
    jitter = options.jitter
    pitch = options.line_spacing * unit * size
    # Letter spacing is selected per character below so spaces and punctuation remain readable.
    cursive = options.style == "cursive"
    space = 0.55 * unit * size * options.word_spacing   # space between words
    left, right = options.margin, options.width - options.margin
    if right - left < 2 * unit * size:
        raise ValueError("Page width is too small for this size.")
    first_baseline = options.margin + 1.2 * unit * size   # leaves headroom for tall letters

    placements = []
    line = 0
    x = float(left)
    last_variant = {}
    text = text.replace("\t", "    ")

    def pick(char):
        variants = _lookup(glyphs, char)
        if variants is None:
            return None
        if len(variants) > 1:                   # avoid repeating the same variant twice in a row
            variants = [v for v in variants if v.variant != last_variant.get(char)] or variants
        chosen = rng.choice(variants)
        last_variant[char] = chosen.variant
        return chosen

    for p_index, paragraph in enumerate(text.split("\n")):
        if p_index > 0:                         # explicit newline
            line += 1
            x = float(left)
        for word in paragraph.split(" "):
            items = []
            word_shift = rng.uniform(-0.035, 0.035) * unit * size * jitter if cursive else 0.0
            for char_index, char in enumerate(word):
                if not char.isprintable():
                    continue
                glyph = pick(char)
                scale = size * (1 + rng.uniform(-0.04 if cursive else -0.08, 0.04 if cursive else 0.08) * jitter)
                width = (glyph.width * scale) if glyph else 0.8 * space
                next_char = word[char_index + 1] if char_index + 1 < len(word) else ""
                joins_next = cursive and char.isascii() and char.islower() and next_char.isascii() and next_char.islower()
                letter_gap = (0.06 if cursive else 0.10) * unit * size * options.letter_spacing
                if cursive:     # letters in one word share a baseline wobble so the joins stay level
                    shift = word_shift + rng.uniform(-0.008, 0.008) * unit * size * jitter
                    angle = rng.uniform(-1.0, 1.0) * jitter
                else:
                    shift = rng.uniform(-0.06, 0.06) * unit * size * jitter
                    angle = rng.uniform(-3.0, 3.0) * jitter
                items.append(dict(
                    glyph=glyph, scale=scale, width=width, angle=angle, shift=shift,
                    joins_next=joins_next, lower=char.isascii() and char.islower(), trim_l=0, trim_r=0,
                    gap=letter_gap * (1 + rng.uniform(-0.2, 0.2) * jitter),
                ))

            for index, item in enumerate(items):      # shorten the dangling tail at each end of a word
                glyph = item["glyph"]
                if not (cursive and glyph and item["lower"]):
                    continue
                if index == 0 or not items[index - 1]["joins_next"]:
                    item["trim_l"] = int(glyph.tail_left * 0.7)
                if not item["joins_next"]:
                    item["trim_r"] = int(glyph.tail_right * 0.7)
                item["width"] = (glyph.width - item["trim_l"] - item["trim_r"]) * item["scale"]

            for current, following in zip(items, items[1:]):
                if current["joins_next"] and current["glyph"] and following["glyph"]:
                    # Slide the next letter left so its entry stroke lies on this one's exit stroke.
                    overlap = min(current["glyph"].tail_right * current["scale"],
                                  following["glyph"].tail_left * following["scale"])
                    current["gap"] = -overlap + (options.letter_spacing - 1.0) * 0.10 * unit * size

            word_width = sum(i["width"] + i["gap"] for i in items)
            if x > left and x + word_width > right:      # word does not fit: wrap it whole
                line += 1
                x = float(left)
            for item in items:
                if x > left and x + item["width"] > right:   # a single huge word: wrap by letter
                    line += 1
                    x = float(left)
                if item["glyph"] is not None:
                    placements.append(Placement(
                        glyph=item["glyph"], x=x,
                        baseline_y=first_baseline + line * pitch + item["shift"],
                        scale=item["scale"], angle=item["angle"],
                        trim_left=item["trim_l"], trim_right=item["trim_r"]))
                # Avoid a negative advance moving a glyph behind the line's left margin.
                x += item["width"] + item["gap"]
            x += space * (1 + rng.uniform(-0.2, 0.2) * jitter)

    n_lines = line + 1
    height = math.ceil(first_baseline + (n_lines - 1) * pitch + 0.5 * unit * size + options.margin)
    return Layout(placements, options.width, height, pitch, first_baseline, n_lines)