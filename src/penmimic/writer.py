"""writer.py - the public API: Writer.from_samples(...).write("text").save("out.png")"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Dict, List, Union

from PIL import Image

from . import glyphs as G
from .glyphs import Glyph
from .layout import Layout, LayoutOptions, layout_text
from .render import PAPER_STYLES, render_frames, render_image


class Page:
    """The result of Writer.write(): a laid-out page you can save as a PNG or animate as a GIF."""

    def __init__(self, layout: "Layout", ink: str, paper: str) -> None:
        self.layout, self.ink, self.paper = layout, ink, paper
        self._image = None

    @property
    def image(self) -> Image.Image:
        """The finished page as a Pillow image (drawn once, then cached)."""
        if self._image is None:
            self._image = render_image(self.layout, self.ink, self.paper)
        return self._image

    def save(self, path: Union[str, Path]) -> Path:
        path = Path(path)
        self.image.save(path)
        return path

    def animate(self, path: Union[str, Path], frame_ms: int = 70, end_pause_ms: int = 1500,
                max_frames: int = 60) -> Path:
        """Save a GIF where the writing appears left to right."""
        frames = render_frames(self.layout, self.ink, self.paper, max_frames=max_frames)
        durations = [frame_ms] * len(frames)
        durations[-1] = end_pause_ms
        path = Path(path)
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations, loop=0)
        return path


class Writer:
    def __init__(self, glyphs: Dict[str, List[Glyph]], seed: int | None = None,
                 style: str = "block") -> None:
        if not glyphs:
            raise ValueError("No glyphs found.")
        if style not in ("block", "cursive"):
            raise ValueError("style must be 'block' or 'cursive'")
        self.glyphs = glyphs
        self.seed = seed
        self.style = style

    @classmethod
    def from_samples(cls, folder: Union[str, Path], seed: int | None = None,
                     style: str = "block") -> "Writer":
        """Build a Writer from a folder of photos of the filled-in template.

        The cut-out characters are saved in <folder>/glyphs/. If the folder has no photos but
        already contains glyphs (glyphs.json), those are loaded instead.
        """
        folder = Path(folder)
        if not folder.is_dir():
            raise FileNotFoundError(f"Samples folder not found: {folder}")
        photos = sorted(p for p in folder.iterdir() if p.suffix.lower() in G.IMAGE_SUFFIXES)
        if photos:
            by_char = G.extract_from_photos(photos, style=style)
            G.save_glyphs(by_char, folder / f"glyphs_{style}")
            return cls(by_char, seed, style)
        candidates = [folder / f"glyphs_{style}"]
        # Legacy cache is safe only for block mode; it has no style metadata.
        if style == "block":
            candidates.append(folder / "glyphs")
            candidates.append(folder)
        for candidate in candidates:
            if (candidate / "glyphs.json").exists():
                return cls(G.load_glyphs(candidate), seed, style)
        raise FileNotFoundError(f"No photos or glyphs.json found in {folder}")

    @classmethod
    def from_glyphs(cls, folder: Union[str, Path], seed: int | None = None) -> "Writer":
        """Load glyphs that were already extracted (a folder containing glyphs.json)."""
        return cls(G.load_glyphs(folder), seed)

    def write(self, text: str, *, size: float = 1.0, ink: str = "#1b1b3a", line_spacing: float = 1.6,
              jitter: float = 1.0, paper: str = "plain", width: int = 1600, margin: int = 80,
              seed: int | None = None, letter_spacing: float = 1.0,
              word_spacing: float = 1.0) -> Page:
        """Lay out `text` and return a Page. Pass seed to get the same result every time."""
        if size <= 0:
            raise ValueError("size must be greater than 0")
        if not 0 <= jitter <= 2:
            raise ValueError("jitter must be between 0 and 2")
        if not 0 <= letter_spacing <= 3:
            raise ValueError("letter_spacing must be between 0 and 3")
        if not 0 <= word_spacing <= 3:
            raise ValueError("word_spacing must be between 0 and 3")
        if paper not in PAPER_STYLES:
            raise ValueError(f"paper must be one of {PAPER_STYLES}")
        options = LayoutOptions(size=size, line_spacing=line_spacing, jitter=jitter,
                                width=width, margin=margin, style=self.style,
                                letter_spacing=letter_spacing, word_spacing=word_spacing)
        rng = random.Random(seed if seed is not None else self.seed)
        return Page(layout_text(text, self.glyphs, options, rng), ink, paper)