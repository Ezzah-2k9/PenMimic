import numpy as np

from penmimic import glyphs as G
from penmimic import template as T


def test_style_bar_distinguishes_block_and_cursive_pages():
    block = np.asarray(T.render_template_page(1, "block"))
    cursive = np.asarray(T.render_template_page(1, "cursive"))
    assert G.detect_template_style(block) == "block"
    assert G.detect_template_style(cursive) == "cursive"


def test_cursive_start_and_finish_guide_dots_are_removed():
    row = T.CHARACTERS.index("a")
    box = np.zeros((T.CELL_H - 2 * G.BOX_PADDING,
                    T.CELL_W - 2 * G.BOX_PADDING), dtype=np.uint8)
    cleaned = G.remove_cursive_join_guides(box, row)
    local_y = T.baseline_y(row) - (T.GRID_TOP + row * T.CELL_H + G.BOX_PADDING)
    left_x = T.JOIN_DOT_OFFSET - G.BOX_PADDING
    right_x = cleaned.shape[1] - T.JOIN_DOT_OFFSET + G.BOX_PADDING - 1
    assert cleaned[local_y, left_x] == 255
    assert cleaned[local_y, right_x] == 255
    # Most of the writing area must remain untouched.
    assert cleaned[local_y, cleaned.shape[1] // 2] == 0


def test_long_baseline_tails_are_trimmed_but_body_remains():
    mask = np.zeros((90, 240), dtype=np.uint8)
    # Simulate a letter body plus long thin lead-in/exit strokes.
    mask[44:47, 8:232] = 1
    mask[28:67, 82:158] = 1
    cleaned = G.trim_cursive_connector_tails(mask, baseline=45)
    assert cleaned[45, 8] == 0
    assert cleaned[45, 231] == 0
    assert cleaned[35:60, 100:140].sum() > 0


