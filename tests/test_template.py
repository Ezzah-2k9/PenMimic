from penmimic import template as T


def test_every_character_has_a_row():
    assert T.PAGE_COUNT * T.ROWS_PER_PAGE >= len(T.CHARACTERS)
    assert "".join(T.page_characters(p) for p in range(1, T.PAGE_COUNT + 1)) == T.CHARACTERS


def test_covers_required_characters():
    for ch in "ABCXYZabcxyz0189.,!?'\"-:;()":
        assert ch in T.CHARACTERS


def test_grid_fits_inside_page_and_clear_of_markers():
    last_x1 = T.cell_box(0, T.VARIANTS - 1)[2]
    last_y1 = T.cell_box(T.ROWS_PER_PAGE - 1, 0)[3]
    assert T.GRID_LEFT > 0 and last_x1 < T.PAGE_W
    assert last_y1 < T.PAGE_H - 150 - T.MARKER_SIZE // 2


def test_template_pdf_has_all_pages(tmp_path):
    from PIL import Image
    path = T.make_template(tmp_path / "t.pdf")
    assert path.exists() and path.stat().st_size > 1000
    assert len(T.render_template_pages()) == T.PAGE_COUNT
    assert isinstance(Image.new("L", (1, 1)), Image.Image)


