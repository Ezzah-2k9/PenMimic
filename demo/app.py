"""
Flask demo page for penmimic: type text, choose options, download the image.

    export PENMIMIC_SAMPLES=my_samples      # folder with photos of your template, or a glyphs folder
    python demo/app.py                      # then open http://127.0.0.1:5000
"""

import io
import os
import re

from flask import Flask, jsonify, render_template, request, send_file

from penmimic import Writer

SAMPLES = os.environ.get("PENMIMIC_SAMPLES", "my_samples")
MAX_TEXT = 600                                   # characters; keeps requests cheap
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")

app = Flask(__name__)
_writers: dict = {}                              # style -> Writer, each loaded once on first use


def get_writer(style: str) -> Writer:
    if style not in _writers:
        _writers[style] = Writer.from_samples(SAMPLES, style=style)
    return _writers[style]


def number(value, default, low, high):
    try:
        return min(max(float(value), low), high)
    except (TypeError, ValueError):
        return default


@app.route("/")
def index():
    return render_template("index.html", max_text=MAX_TEXT)


@app.route("/render", methods=["POST"])
def render():
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()[:MAX_TEXT]
    if not text:
        return jsonify(error="Please type some text."), 400
    ink = data.get("ink", "#1b1b3a")
    if not HEX_COLOR.match(str(ink)):
        return jsonify(error="Ink colour must look like #1b1b3a."), 400
    paper = data.get("paper", "plain")
    if paper not in ("plain", "lined"):
        return jsonify(error="Paper must be plain or lined."), 400

    style = data.get("style", "block")
    if style not in ("block", "cursive"):
        return jsonify(error="Style must be block or cursive."), 400
    try:
        writer = get_writer(style)
    except (FileNotFoundError, ValueError) as error:
        return jsonify(error=f"No {style} samples available: {error}"), 400

    page = writer.write(
        text, ink=ink, paper=paper,
        size=number(data.get("size"), 1.0, 0.4, 2.0),
        line_spacing=number(data.get("line_spacing"), 1.6, 1.0, 3.0),
        jitter=number(data.get("jitter"), 1.0, 0.0, 2.0),
        letter_spacing=number(data.get("letter_spacing"), 1.0, 0.0, 3.0),
        word_spacing=number(data.get("word_spacing"), 1.0, 0.0, 3.0),
    )
    buffer = io.BytesIO()
    page.image.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png", download_name="handwriting.png")


if __name__ == "__main__":
    app.run(debug=False)