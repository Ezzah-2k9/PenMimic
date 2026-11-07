import pytest
from PIL import Image


def test_three_line_example_makes_a_png(writer, tmp_path):
    out = writer.write("Hello world").save(tmp_path / "note.png")
    image = Image.open(out)
    assert image.size[0] == 1600 and image.size[1] > 100
    assert image.convert("L").getextrema()[0] < 100        # there is dark ink on the page


def test_animate_makes_a_multi_frame_gif(writer, tmp_path):
    out = writer.write("Hello world").animate(tmp_path / "note.gif")
    gif = Image.open(out)
    assert gif.n_frames > 3


def test_ink_colour_is_used(writer):
    image = writer.write("Hello", ink="#ff0000", jitter=0).image
    import numpy as np
    px = np.array(image)
    reds = (px[..., 0] > 200) & (px[..., 1] < 80) & (px[..., 2] < 80)
    assert reds.sum() > 100


def test_lined_paper_differs_from_plain(writer):
    plain = writer.write("Hello", paper="plain", seed=3).image
    lined = writer.write("Hello", paper="lined", seed=3).image
    assert plain.tobytes() != lined.tobytes()


def test_size_option_makes_text_bigger(writer):
    small = writer.write("Hello", size=0.5, seed=1).layout
    large = writer.write("Hello", size=1.5, seed=1).layout
    assert large.pitch > small.pitch


def test_bad_options_are_rejected(writer):
    with pytest.raises(ValueError):
        writer.write("x", paper="graph")
    with pytest.raises(ValueError):
        writer.write("x", size=0)
    with pytest.raises(ValueError):
        writer.write("x", ink="notacolour").image


def test_glyph_folder_round_trip(writer, samples_dir):
    from penmimic import Writer
    again = Writer.from_samples(samples_dir)          # now also has a glyphs/ folder next to the photos
    assert again.write("ok", seed=1).image.size == writer.write("ok", seed=1).image.size


def test_missing_folder_gives_clear_error(tmp_path):
    from penmimic import Writer
    with pytest.raises(FileNotFoundError):
        Writer.from_samples(tmp_path / "nope")


def test_command_line(samples_dir, tmp_path):
    from penmimic.cli import main
    out = tmp_path / "cli.png"
    assert main(["Hi there", "--samples", str(samples_dir), "-o", str(out), "--seed", "1"]) == 0
    assert out.exists()


def test_command_line_makes_template(tmp_path):
    from penmimic.cli import main
    assert main(["--make-template", str(tmp_path / "t.pdf")]) == 0
    assert (tmp_path / "t.pdf").exists()


