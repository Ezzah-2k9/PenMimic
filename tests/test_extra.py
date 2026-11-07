import importlib.util
import random
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from penmimic import glyphs as G
from penmimic.glyphs import Glyph
from penmimic.layout import LayoutOptions, layout_text


def test_tails_are_shortened_not_removed_and_body_kept():
    mask = np.zeros((90, 240), dtype=np.uint8)
    mask[44:47, 8:232] = 1
    mask[28:67, 82:158] = 1
    cleaned = G.trim_cursive_connector_tails(mask, baseline=45, keep=20)
    assert cleaned[45, 70] == 1 and cleaned[45, 170] == 1
    assert cleaned[45, 40] == 0 and cleaned[45, 200] == 0
    assert cleaned[35:60, 100:140].sum() > 0


def test_detached_specks_on_baseline_are_removed_but_i_dot_stays():
    alpha = np.zeros((100, 80), dtype=np.uint8)
    alpha[30:90, 38:44] = 255
    alpha[10:16, 38:44] = 255
    alpha[78:83, 4:9] = 255
    out = G.remove_baseline_specks(alpha, baseline=80)
    assert out[12, 40] == 255 and out[80, 6] == 0 and out[60, 40] == 255


def test_letter_and_word_spacing_options_change_width():
    glyphs = {c: [Glyph(c, 0, Image.new("L", (40, 60), 255), 50)] for c in "ab "}

    def right_edge(**kw):
        lay = layout_text("ab ab", glyphs, LayoutOptions(jitter=0, **kw), random.Random(1))
        return max(p.x for p in lay.placements)

    assert right_edge(letter_spacing=2.0) > right_edge(letter_spacing=1.0) > right_edge(letter_spacing=0.2)
    assert right_edge(word_spacing=2.0) > right_edge(word_spacing=1.0)


def test_cursive_letters_overlap_their_tails():
    glyphs = {c: [Glyph(c, 0, Image.new("L", (60, 60), 255), 50, 20, 20)] for c in "ab"}
    lay = layout_text("ab", glyphs, LayoutOptions(jitter=0, style="cursive"), random.Random(1))
    first, second = lay.placements
    visible = 60 - first.trim_left - first.trim_right
    assert second.x - first.x < visible


def test_demo_spacing_options_work_and_bad_style_is_rejected(samples_dir, monkeypatch):
    pytest.importorskip("flask")
    monkeypatch.setenv("PENMIMIC_SAMPLES", str(samples_dir))
    path = Path(__file__).resolve().parents[1] / "demo" / "app.py"
    spec = importlib.util.spec_from_file_location("demo_app_extra", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["demo_app_extra"] = module
    spec.loader.exec_module(module)
    client = module.app.test_client()
    ok = client.post("/render", json={"text": "hello", "style": "block", "letter_spacing": 2, "word_spacing": 0.5})
    assert ok.status_code == 200
    assert client.post("/render", json={"text": "hi", "style": "gothic"}).status_code == 400
