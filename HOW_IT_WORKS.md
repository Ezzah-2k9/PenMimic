# How penmimic works

Written for a smart student who has not seen the code.

## The big idea
1. You write every character five times on a printed sheet.
2. We photograph the sheet, find each box, and cut out the ink. That gives a "font" made of your real letters.
3. To write a sentence, we pick a letter image for every character, set them in a row, add small random
   wobbles, and paste them onto paper.

No machine learning is used in version 0.1; it is image processing and layout.

## Block vs cursive
There are two printable templates with the **same grid** (same box positions, same markers), so one reader handles both:
- **Block**: plain boxes with a dotted baseline.
- **Cursive**: same boxes, plus a solid black **style bar** in the header, an x-height line, and a filled start dot
  and hollow end dot on each a-z row.

How the program tells them apart: `detect_template_style` checks whether the style bar is black. Pick the style you
want with `Writer.from_samples(folder, style="cursive")`. Pages of the other style in the same folder are skipped.

Cursive extras:
1. `remove_cursive_join_guides` erases the printed dots so they are not read as ink.
2. `trim_cursive_connector_tails` trims long thin lead-in/exit strokes near the baseline, keeping the letter body, loops and descenders.
3. In `layout.py`, two lowercase letters in the same word get a smaller gap (they overlap slightly so strokes meet), and cursive uses less tilt jitter so words stay on the line.

## Files (in `src/penmimic/`)

### `template.py` - the sheet
Draws the printable sheet and defines where every box is (page size, box size, rows per page).
**Both** the sheet and the photo reader import these numbers, so they always agree.
Each page has:
- four solid black squares in the corners (so we can straighten the photo),
- small header squares: one square = page 1, two = page 2 ... (so we know which page a photo is),
- a row per character with five boxes, each with a pale dotted baseline to write on.

### `glyphs.py` - from photo to letters
1. **`find_marker_centers`** turns the photo black-and-white (Otsu's method picks the cut-off automatically),
   finds blobs, and keeps the four biggest solid squares. A solid square fills its bounding box; a letter does not.
2. **`rectify`** uses a *perspective transform*: we know where the four squares should be on a flat page and where
   they are in the photo, so OpenCV computes the warp that flattens the photo into a perfect A4 page.
3. **`normalise_lighting`** estimates how bright the blank paper is in each place (a morphological *close* erases
   the thin pen strokes, then we blur) and divides the photo by it. Shadows disappear and paper becomes white everywhere.
4. **`read_page_number`** counts the header squares.
5. **`cut_glyph`** looks inside one box (ignoring a margin so the printed border is not included), keeps dark pixels,
   throws away tiny specks, crops tightly, and saves an **alpha mask** (how much ink at each pixel, with soft edges).
   It also records the **baseline**: how many pixels down from the top of the crop the dotted line was.
   This is why a comma hangs below the line and an apostrophe floats above it.
6. **`save_glyphs` / `load_glyphs`** write one transparent PNG per letter (`U0041_v2.png` = "A", variant 2) plus `glyphs.json`.

### `layout.py` - where everything goes (no drawing here)
- Picks a random variant for each character, avoiding the same variant twice in a row.
- **Jitter** multiplies small random numbers: size +-8%, tilt +-3 degrees, height +-6% of a letter, gap +-40%.
  `jitter=0` turns it all off.
- Measures words; if a word would cross the right margin it moves to the next line. A word too long for a line is broken by letter.
- Fallbacks: curly quotes become straight ones; a missing character tries the other case, then `?`, then leaves a gap.
- Uses a seeded random generator so `seed=42` gives the same page every time.

### `render.py` - drawing
Draws paper (plain or ruled), then for each letter: scale and tilt its mask, line its baseline up with the line,
and paste a block of the ink colour through the mask. Because the glyph is only a mask, any ink colour works.
For the GIF, we paste letters one by one and save a snapshot every few letters.

### `writer.py` - the public API
`Writer.from_samples(folder)` runs the extraction. `Writer.write(text, ...)` does layout and returns a `Page`;
`Page.save()` writes a PNG and `Page.animate()` writes a GIF.

### `cli.py`
The `penmimic` command.

### `demo/`
A tiny Flask site. The server loads your letters once, and `/render` returns a PNG. Text length, size and
colour are validated so the server can't be overloaded or sent bad input.

### `tests/`
We cannot ship someone's real handwriting, so tests make fake handwriting from a computer font, "photograph" it
with perspective, shadows and noise, and check that all 365 boxes are recovered, baselines are right, text wraps
inside the margins, and the same seed gives the same page.

## Design choices
- One file defines the page geometry, so the printer and the reader cannot drift apart.
- Markers + perspective warp, instead of asking for a perfectly scanned page.
- Masks instead of coloured images, so ink colour is free and edges stay smooth.
- Layout is separate from drawing, so layout can be tested without images.
- Clear errors (`corner squares`, `which template page`) instead of silent bad output.


