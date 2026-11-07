# penmimic

[![PyPI](https://img.shields.io/pypi/v/penmimic)](https://pypi.org/project/penmimic/)
[![Tests](https://github.com/Ezzah-2k9/penmimic/actions/workflows/tests.yml/badge.svg)](https://github.com/Ezzah-2k9/penmimic/actions)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Write any text in **your own handwriting** from Python. Fill in a printable template, photograph it, and
`penmimic` cuts out your letters and uses them to write whatever you like, as a PNG or an animated GIF.

## The problem
Typed text feels impersonal. Existing handwriting tools are closed, limited, or hard to use from code.

## The solution
A small library with a short API:

```python
from penmimic import Writer

w = Writer.from_samples("my_samples/")
w.write("Hello world").save("note.png")
w.write("Hello world").animate("note.gif")
```

Each letter is picked at random from five of your own versions, then given a tiny random change in size,
tilt, height and spacing, so the page does not look copy-pasted.

## Install

```bash
pip install penmimic
```
Python 3.10+. For the optional web demo: `pip install "penmimic[demo]"`.

## Use it

**1. Get and print the template(s)** (5 A4 pages each). There are two: **block** letters and **cursive**.

Download the ready-made PDFs:
- [Block letters template (PDF)](https://github.com/Ezzah-2k9/penmimic/raw/main/templates/penmimic_block_template.pdf)
- [Cursive template (PDF)](https://github.com/Ezzah-2k9/penmimic/raw/main/templates/penmimic_cursive_template.pdf)

Or generate them yourself after `pip install penmimic`:
```bash
penmimic --make-templates templates/                 # makes both PDFs
penmimic --make-template block.pdf                   # just block
penmimic --make-template cursive.pdf --style cursive # just cursive
```
In the cursive sheet, every a-z box has a dotted baseline, an x-height line, a filled dot (start) and a hollow
dot (end). Write one natural letter with a short lead-in at the filled dot and a short flick at the hollow dot.
You do not have to fill in both sheets: fill the style(s) you want. Photos of both can sit in the same folder.

**2. Fill it in** with a dark pen. Write every character in every box, sitting on the dotted line.

**3. Photograph each page.** Whole page in view, flat, good light, plain surface, held upright (portrait).
Put the photos in a folder, e.g. `my_samples/`. File names do not matter: each page is recognised from the
small squares in its header.

**4. Write.**
```python
from penmimic import Writer
w = Writer.from_samples("my_samples/", style="cursive")   # or "block" (default); letters saved in my_samples/glyphs_cursive/
w.write("Dear diary,\nToday was good.", size=1.2, ink="navy", paper="lined",
        line_spacing=1.8, jitter=0.8, seed=42).save("diary.png")
```

Command line:
```bash
penmimic "Hello world" --samples my_samples --style cursive -o note.png
penmimic "Hello world" --samples my_samples -o note.gif --paper lined --ink navy
```

### Options for `write()`
| Option | Default | Meaning |
|---|---|---|
| `letter_spacing` | 1.0 | 0-3. Gap between letters (in cursive, above 1 opens the joins) |
| `word_spacing` | 1.0 | 0-3. Gap between words |
| `size` | 1.0 | Text size (1.0 = as written on the template) |
| `ink` | `#1b1b3a` | Ink colour: name or hex |
| `line_spacing` | 1.6 | Gap between lines, as a multiple of a typical letter height |
| `jitter` | 1.0 | 0 = identical letters, 1 = natural, 2 = messy (max) |
| `paper` | `plain` | `plain` or `lined` |
| `width` / `margin` | 1600 / 80 | Page size in pixels |
| `seed` | None | Same seed = same result every time |

## Demo website
```bash
pip install -e ".[demo]"
export PENMIMIC_SAMPLES=my_samples     # Windows PowerShell: $env:PENMIMIC_SAMPLES="my_samples"
python demo/app.py                     # open http://127.0.0.1:5000
```

## Results
- 44 automated tests pass (`pytest`). They use *synthetic* "handwriting" made from a computer font, photographed
  with simulated perspective, shadow and noise. They prove the pipeline works, not that it looks good on every
  real hand.

## Limitations
- Needs a clean template: a pen that is too light, boxes crossed by ink, or a dark/uneven background can break extraction.
- Cursive mode overlaps and tightens letters inside a word so they touch, but it still pastes separate letter images; it does not draw one continuous pen stroke.
- Only the characters on the template (A-Z, a-z, 0-9, `.,!?'"-:;()`). Others fall back to the other case,
  then `?`, then a blank gap.
- Photos must show the whole page, roughly upright. Very strong shadows or extreme angles fail with a clear error.
- It copies your letters; it does not learn how you write. A neural stroke model is planned for version 0.2.
- Left-to-right scripts only.

## Credits
- Built by Ezzah Najmal.
- Libraries: OpenCV, Pillow, NumPy, Flask, pytest.

## Licence
MIT. See [LICENSE](LICENSE). Handwriting samples are personal data: only use your own or ones you have permission to use.