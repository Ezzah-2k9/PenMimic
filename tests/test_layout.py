import random

import pytest

from penmimic.layout import LayoutOptions, layout_text


def lay(writer, text, seed=0, **kw):
    return layout_text(text, writer.glyphs, LayoutOptions(**kw), random.Random(seed))


def test_same_seed_gives_identical_layout(writer):
    a, b = lay(writer, "Hello world", seed=5), lay(writer, "Hello world", seed=5)
    assert [(p.x, p.baseline_y, p.scale) for p in a.placements] == [(p.x, p.baseline_y, p.scale) for p in b.placements]


def test_different_seed_changes_layout(writer):
    a, b = lay(writer, "Hello world", seed=1), lay(writer, "Hello world", seed=2)
    assert [p.angle for p in a.placements] != [p.angle for p in b.placements]


def test_zero_jitter_is_perfectly_regular(writer):
    layout = lay(writer, "aaaa", jitter=0)
    assert len({p.scale for p in layout.placements}) == 1
    assert {p.angle for p in layout.placements} == {0.0}
    assert len({p.baseline_y for p in layout.placements}) == 1


def test_one_placement_per_visible_character(writer):
    assert len(lay(writer, "Hi there!").placements) == len("Hithere!")


def test_long_text_wraps_inside_margins(writer):
    layout = lay(writer, "The quick brown fox jumps over the lazy dog. " * 4, width=900)
    assert layout.n_lines > 1
    for p in layout.placements:
        assert p.x >= 80 - 1
        assert p.x + p.glyph.width * p.scale <= 900 - 80 + 1


def test_newline_starts_a_new_line(writer):
    assert lay(writer, "one\ntwo").n_lines == 2


def test_word_longer_than_a_line_is_broken_by_letter(writer):
    layout = lay(writer, "W" * 60, width=700)
    assert layout.n_lines > 1


def test_missing_character_falls_back_without_crashing(writer):
    layout = lay(writer, "caf\u00e9 \u2192 ok")     # e-acute and an arrow are not on the template
    assert len(layout.placements) >= 5


def test_curly_quotes_use_plain_quote_glyphs(writer):
    layout = lay(writer, "\u201chi\u201d")
    assert len(layout.placements) == 4


def test_tiny_page_width_is_rejected(writer):
    with pytest.raises(ValueError):
        lay(writer, "x", width=100)


def test_each_line_is_one_pitch_below_the_last(writer):
    layout = lay(writer, "a\nb\nc", jitter=0)
    ys = sorted({round(p.baseline_y, 3) for p in layout.placements})
    assert [round(b - a, 3) for a, b in zip(ys, ys[1:])] == [round(layout.pitch, 3)] * 2


