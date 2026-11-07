"""
glyphs.py - turn photos of the filled-in template into one transparent PNG per character.

Pipeline for each photo:
    1. find the four black corner squares              (find_marker_centers)
    2. warp the photo so the page is flat and upright  (rectify)
    3. even out shadows and uneven lighting            (normalise_lighting)
    4. read which page it is from the header dots      (read_page_number)
    5. cut each box, keep the ink, crop, record baseline (cut_glyph)
"""

import json
import warnings
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from . import template as T

INK_THRESHOLD = 150      # after lighting is evened out, pixels darker than this are ink
BOX_PADDING = 14         # ignore this many pixels inside each box edge (the printed border)
MIN_SPECK = 20           # connected ink blobs smaller than this many pixels are dust
CURSIVE_TAIL_KEEP = 24   # cursive: keep at most this many px of entry/exit stroke on each side
MIN_INK = 40             # a box with less ink than this counts as empty
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


@dataclass
class Glyph:
    """One cut-out character. `alpha` is the ink strength (0 = paper, 255 = solid ink)."""
    char: str
    variant: int
    alpha: Image.Image      # mode "L"
    baseline: int           # pixels from the top of the image down to the writing baseline
    tail_left: int = 0      # cursive only: length of the entry stroke left of the letter body (px)
    tail_right: int = 0     # cursive only: length of the exit stroke right of the letter body (px)

    @property
    def width(self):
        return self.alpha.width

    @property
    def height(self):
        return self.alpha.height

    def to_rgba(self):
        black = Image.new("L", self.alpha.size, 0)
        return Image.merge("RGBA", (black, black, black, self.alpha))


# ---------------------------------------------------------------------------------------------
# Steps 1-4: make the photo flat, even and readable
# ---------------------------------------------------------------------------------------------
def find_marker_centers(gray):
    """Centres of the four corner squares, ordered top-left, top-right, bottom-right, bottom-left."""
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    candidates = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < 0.0002 * gray.size:
            continue
        (cx, cy), (w, h), _ = cv2.minAreaRect(contour)   # rotation-proof bounding box
        if w == 0 or h == 0:
            continue
        fill = area / (w * h)                            # a solid square fills its box (~1.0)
        squareness = min(w, h) / max(w, h)
        if fill > 0.85 and squareness > 0.7:
            candidates.append((area, cx, cy))

    if len(candidates) < 4:
        raise ValueError("Could not find the 4 black corner squares. Make sure the whole page "
                         "is visible, flat, well lit and on a plain surface.")
    candidates.sort(reverse=True)
    pts = np.array([[cx, cy] for _, cx, cy in candidates[:4]], dtype=np.float32)

    total, diff = pts.sum(axis=1), pts[:, 1] - pts[:, 0]
    return np.array([pts[np.argmin(total)], pts[np.argmin(diff)],
                     pts[np.argmax(total)], pts[np.argmax(diff)]], dtype=np.float32)


def shrink_if_huge(gray):
    """Phone/scanner images can be 6000+ px wide. Shrink them with area averaging first.

    Warping straight from a huge image samples sparse pixels and makes thin pen strokes faint
    or broken. INTER_AREA averages instead, which keeps strokes dark and smooth.
    """
    target_width = int(T.PAGE_W * 1.2)
    if gray.shape[1] > target_width * 1.15:
        factor = target_width / gray.shape[1]
        gray = cv2.resize(gray, None, fx=factor, fy=factor, interpolation=cv2.INTER_AREA)
    return gray


def rectify(gray):
    """Warp the photo to a flat, upright A4 page at 300 dpi."""
    gray = shrink_if_huge(gray)
    source = find_marker_centers(gray)
    target = np.array(T.MARKER_CENTERS, dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(source, target)
    return cv2.warpPerspective(gray, matrix, (T.PAGE_W, T.PAGE_H),
                               flags=cv2.INTER_LINEAR, borderValue=255)


def normalise_lighting(gray):
    """Divide by an estimate of the paper brightness so shadows disappear (paper -> ~255)."""
    background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, np.ones((45, 45), np.uint8))  # erases pen strokes
    background = cv2.GaussianBlur(background, (0, 0), 25)
    return cv2.divide(gray, background, scale=255)


def marker_blackness(rectified):
    """How dark the printed solid-black squares look in this scan, relative to the paper (0-255).

    A good scan gives ~0. A washed-out scan gives e.g. 100. We use it to stretch contrast.
    """
    half = T.MARKER_SIZE // 4
    patches = [rectified[cy - half:cy + half, cx - half:cx + half] for cx, cy in T.MARKER_CENTERS]
    black = float(np.median([np.median(p) for p in patches]))
    paper = float(np.median(rectified))
    return 255.0 * black / max(paper, 1.0)


def stretch_contrast(normalised, blackness):
    """Make a washed-out scan look like a normal one: scale 'darkness' so the markers become black."""
    available = max(255.0 - blackness, 1.0)
    scale = min(max(255.0 / available, 1.0), 3.0)         # never weaken, never boost more than 3x
    darkness = (255.0 - normalised.astype(np.float32)) * scale
    return np.clip(255.0 - darkness, 0, 255).astype(np.uint8)


def read_page_number(normalised):
    """Count the small header squares: N squares means page N."""
    x0, y0, x1, y1 = T.PAGE_NUMBER_REGION
    ink = (normalised[y0:y1, x0:x1] < INK_THRESHOLD).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(ink)
    return sum(1 for i in range(1, count) if stats[i, cv2.CC_STAT_AREA] >= 0.5 * T.PAGE_DOT ** 2)


# ---------------------------------------------------------------------------------------------
# Step 5: cut a box into a glyph
# ---------------------------------------------------------------------------------------------
def cut_glyph(box, baseline_in_box, char, variant):
    """box: grayscale crop (paper ~255, ink dark). Returns a Glyph, or None if the box is empty."""
    mask = (box < INK_THRESHOLD).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    big_enough = np.zeros(count, dtype=bool)
    big_enough[1:] = stats[1:, cv2.CC_STAT_AREA] >= MIN_SPECK     # label 0 is the background
    keep = big_enough[labels].astype(np.uint8)
    if keep.sum() < MIN_INK:
        return None

    ys, xs = np.nonzero(keep)
    pad = 3
    top, bottom = max(ys.min() - pad, 0), min(ys.max() + 1 + pad, box.shape[0])
    left, right = max(xs.min() - pad, 0), min(xs.max() + 1 + pad, box.shape[1])

    # Soft edges: darker pixel -> more opaque. Only near real ink, so faint guide lines vanish.
    strength = np.clip((200.0 - box) * (255.0 / (200.0 - 70.0)), 0, 255)
    near_ink = cv2.dilate(keep, np.ones((5, 5), np.uint8))
    alpha = (strength * near_ink).astype(np.uint8)[top:bottom, left:right]

    return Glyph(char=char, variant=variant, alpha=Image.fromarray(alpha),
                 baseline=int(baseline_in_box - top))


def detect_template_style(normalised):
    """Return 'cursive' when the printed black style bar is present; otherwise 'block'."""
    x0, y0, x1, y1 = T.STYLE_BAR
    patch = normalised[y0:y1, x0:x1]
    # The block template leaves this header patch white; cursive prints a solid black bar.
    return "cursive" if patch.size and float(np.mean(patch)) < 110 else "block"


def remove_cursive_join_guides(box, row):
    """Erase only the template's printed start/end circles, leaving pen strokes intact."""
    clean = box.copy()
    local_y = T.baseline_y(row) - (T.GRID_TOP + row * T.CELL_H + BOX_PADDING)
    radius = 19
    # Also recognize the older, wider-spaced dots (offset 48) from already-filled sheets.
    offsets = {getattr(T, "JOIN_DOT_OFFSET", 48), 48}
    for offset in offsets:
        left_x = offset - BOX_PADDING
        right_x = clean.shape[1] - offset + BOX_PADDING - 1
        cv2.circle(clean, (left_x, local_y), radius, 255, thickness=-1)
        cv2.circle(clean, (right_x, local_y), radius, 255, thickness=-1)
    return clean


def cursive_body_span(mask):
    """(left, right) columns of the letter body, or None.

    A pen stroke that just runs along the baseline (an entry/exit tail) is only a few pixels
    tall. The body of a letter (loops, stems, bowls) is much taller. So the body is the span
    between the first and last "tall" ink column; everything outside it is a tail.
    """
    ink = np.asarray(mask) > 0
    if not ink.any():
        return None
    rows = np.flatnonzero(ink.any(axis=1))
    height = int(rows[-1] - rows[0] + 1)
    top = ink.argmax(axis=0)
    bottom = ink.shape[0] - 1 - ink[::-1].argmax(axis=0)
    extent = np.where(ink.any(axis=0), bottom - top + 1, 0)
    tall = np.flatnonzero(extent >= max(14, round(0.18 * height)))
    if tall.size == 0:
        return None
    return int(tall[0]), int(tall[-1])


def trim_cursive_connector_tails(mask, baseline=0, keep=0):
    """Cut entry/exit strokes down to `keep` pixels beyond the letter body (0 removes them)."""
    span = cursive_body_span(mask)
    if span is None:
        return mask
    left, right = span
    cleaned = mask.copy()
    cleaned[:, :max(0, left - keep)] = 0
    cleaned[:, right + 1 + keep:] = 0
    return cleaned


def remove_baseline_specks(alpha, baseline):
    """Delete small detached blobs sitting on the baseline (leftovers of the printed guide dots).

    The dot of an 'i' or 'j' is far above the baseline, so it is never touched.
    """
    ink = (alpha > 60).astype(np.uint8)
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(ink, connectivity=8)
    if count <= 2:
        return alpha
    largest = stats[1:, cv2.CC_STAT_AREA].max()
    near = max(16, round(0.12 * alpha.shape[0]))
    cleaned = alpha.copy()
    for i in range(1, count):
        small = stats[i, cv2.CC_STAT_AREA] < 0.15 * largest
        if small and abs(centroids[i][1] - baseline) <= near:
            cleaned[labels == i] = 0
    return cleaned


def finish_cursive_glyph(glyph, keep=CURSIVE_TAIL_KEEP):
    """Clean a cursive letter in place: drop specks, shorten tails, record tail lengths."""
    alpha = remove_baseline_specks(np.asarray(glyph.alpha).copy(), glyph.baseline)
    span = cursive_body_span(alpha > 60)
    left, right = span if span else (0, alpha.shape[1] - 1)
    alpha[:, :max(0, left - keep)] = 0
    alpha[:, right + 1 + keep:] = 0
    bounds = Image.fromarray(alpha).getbbox()
    if not bounds:
        return
    glyph.alpha = Image.fromarray(alpha).crop(bounds)
    glyph.baseline -= bounds[1]
    glyph.tail_left = max(0, left - bounds[0])
    glyph.tail_right = max(0, bounds[2] - 1 - right)


def extract_page(normalised, page, style="block"):
    """Extract one page; remove printed cursive start/finish markers before reading ink."""
    glyphs, missing = [], []
    for row, char in enumerate(T.page_characters(page)):
        for variant in range(T.VARIANTS):
            x0, y0, x1, y1 = T.cell_box(row, variant)
            box = normalised[y0 + BOX_PADDING:y1 - BOX_PADDING, x0 + BOX_PADDING:x1 - BOX_PADDING]
            if style == "cursive" and char.islower():
                box = remove_cursive_join_guides(box, row)
            baseline_in_box = T.baseline_y(row) - (y0 + BOX_PADDING)
            glyph = cut_glyph(box, baseline_in_box, char, variant)
            if glyph is not None and style == "cursive" and char.islower():
                finish_cursive_glyph(glyph)
            (glyphs if glyph else missing).append(glyph or (char, variant))
    return glyphs, missing


def extract_from_photos(paths, style="block"):
    """Read only pages of the requested style. Returns {char: [Glyph, ...]}."""
    if style not in T.STYLES:
        raise ValueError(f"style must be one of {T.STYLES}, not {style!r}")
    by_char, missing_all = {}, []
    for path in paths:
        image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"Could not read image: {path}")
        try:
            rectified = rectify(image)
            normalised = stretch_contrast(normalise_lighting(rectified), marker_blackness(rectified))
        except ValueError as error:
            raise ValueError(f"{Path(path).name}: {error}") from None
        page = read_page_number(normalised)
        page_style = detect_template_style(normalised)
        if page_style != style:
            continue
        if not 1 <= page <= T.PAGE_COUNT:
            raise ValueError(f"{Path(path).name}: could not tell which template page this is "
                             f"(read {page}). Photograph the whole page, including the top.")
        glyphs, missing = extract_page(normalised, page, style=page_style)
        missing_all += missing
        for glyph in glyphs:
            by_char.setdefault(glyph.char, []).append(glyph)

    if not by_char:
        raise ValueError(f"No {style} template pages found in the samples folder.")
    if missing_all:
        chars = "".join(sorted({c for c, _ in missing_all}))
        warnings.warn(f"{len(missing_all)} empty or unreadable boxes (characters: {chars}). "
                      "Missing variants will be skipped; missing characters use a fallback.")
    return by_char


# ---------------------------------------------------------------------------------------------
# Saving and loading glyph PNGs
# ---------------------------------------------------------------------------------------------
def glyph_filename(char, variant):
    return f"U{ord(char):04X}_v{variant + 1}.png"          # e.g. U0041_v2.png = 'A', 2nd variant


def save_glyphs(by_char, out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    index = {}
    for glyphs in by_char.values():
        for g in glyphs:
            name = glyph_filename(g.char, g.variant)
            g.to_rgba().save(out_dir / name)
            index[name] = {"char": g.char, "variant": g.variant, "baseline": g.baseline,
                           "tail_left": g.tail_left, "tail_right": g.tail_right}
    (out_dir / "glyphs.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    return out_dir


def load_glyphs(folder):
    folder = Path(folder)
    index = json.loads((folder / "glyphs.json").read_text(encoding="utf-8"))
    by_char = {}
    for name, info in index.items():
        alpha = Image.open(folder / name).convert("RGBA").getchannel("A")
        by_char.setdefault(info["char"], []).append(
            Glyph(info["char"], info["variant"], alpha, info["baseline"],
                  info.get("tail_left", 0), info.get("tail_right", 0)))
    return by_char