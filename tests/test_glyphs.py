import warnings

import pytest

from penmimic import glyphs as G
from penmimic import template as T


def test_all_characters_and_variants_are_extracted(writer):
    for char in T.CHARACTERS:
        assert len(writer.glyphs[char]) == T.VARIANTS, f"missing variants for {char!r}"


def test_glyphs_are_transparent_pngs_with_ink(writer, tmp_path):
    G.save_glyphs(writer.glyphs, tmp_path)
    assert (tmp_path / "glyphs.json").exists()
    assert (tmp_path / "U0041_v1.png").exists()          # 'A', first variant
    glyph = writer.glyphs["A"][0]
    assert glyph.to_rgba().mode == "RGBA"
    assert glyph.alpha.getextrema()[1] > 200               # there is solid ink in it


def test_baseline_is_recorded(writer):
    a = writer.glyphs["a"][0]                              # sits on the baseline
    g = writer.glyphs["g"][0]                              # has a descender
    assert abs(a.baseline - a.height) < 12
    assert g.baseline < g.height - 15


def test_saved_glyphs_can_be_loaded_again(writer, tmp_path):
    G.save_glyphs(writer.glyphs, tmp_path)
    loaded = G.load_glyphs(tmp_path)
    assert set(loaded) == set(writer.glyphs)
    assert loaded["a"][0].baseline in {g.baseline for g in writer.glyphs["a"]}


def test_missing_characters_trigger_a_warning(tmp_path):
    from helpers import write_photos
    folder = write_photos(tmp_path / "s", skip="C", pages=[1])
    photos = sorted(folder.iterdir())
    with pytest.warns(UserWarning, match="empty"):
        by_char = G.extract_from_photos(photos)
    assert "C" not in by_char and "A" in by_char


def test_unreadable_photo_gives_clear_error(tmp_path):
    from PIL import Image
    Image.new("L", (800, 1000), 255).save(tmp_path / "blank.png")
    with pytest.raises(ValueError, match="corner squares"):
        G.extract_from_photos([tmp_path / "blank.png"])


def test_no_warning_when_everything_is_filled(samples_dir):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        G.extract_from_photos(sorted(samples_dir.glob("photo_1.jpg")))


