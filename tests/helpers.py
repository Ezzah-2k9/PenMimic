"""Helpers that fake a person filling in the template and photographing it (no real handwriting needed)."""

import random

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from penmimic import template as T


def fill_page(page, seed=0, skip=()):
    """Draw each character in every box with a plain font, wobbling a little. `skip` = chars to leave blank."""
    rng = random.Random(seed + page)
    img = T.render_template_page(page)
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=100)
    for row, char in enumerate(T.page_characters(page)):
        if char in skip:
            continue
        for variant in range(T.VARIANTS):
            x0, y0, x1, y1 = T.cell_box(row, variant)
            x = x0 + 120 + rng.randint(-30, 30)
            y = T.baseline_y(row) + rng.randint(-4, 4)
            draw.text((x, y), char, font=font, fill=25, anchor="ls")   # anchor "ls" = left, baseline
    return img


def photograph(page_img, seed=0):
    """Fake a phone photo: smaller, slightly skewed, uneven lighting, a little noise."""
    rng = np.random.default_rng(seed)
    gray = np.array(page_img)
    out_w, out_h = 1700, 2400
    src = np.float32([[0, 0], [T.PAGE_W, 0], [T.PAGE_W, T.PAGE_H], [0, T.PAGE_H]])
    dst = np.float32([[90, 120], [out_w - 60, 70], [out_w - 110, out_h - 90], [70, out_h - 140]])
    matrix = cv2.getPerspectiveTransform(src, dst)
    photo = cv2.warpPerspective(gray, matrix, (out_w, out_h), borderValue=200).astype(np.float32)
    gradient = np.linspace(0.75, 1.0, out_w, dtype=np.float32)[None, :]   # shadow on one side
    photo = photo * gradient + rng.normal(0, 3, photo.shape)
    return np.clip(photo, 0, 255).astype(np.uint8)


def write_photos(folder, skip=(), pages=None):
    folder.mkdir(parents=True, exist_ok=True)
    for page in (pages or range(1, T.PAGE_COUNT + 1)):
        photo = photograph(fill_page(page, skip=skip), seed=page)
        Image.fromarray(photo).save(folder / f"photo_{page}.jpg", quality=92)
    return folder


