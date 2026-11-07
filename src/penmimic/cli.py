"""Command line:  penmimic "Hello world" --samples my_samples -o note.png"""

import argparse
import sys

from .template import make_both_templates, make_template
from .writer import Writer


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="penmimic", description="Write text in your own handwriting.")
    p.add_argument("text", nargs="?", help="the text to write")
    p.add_argument("--samples", help="folder with photos of your filled-in template (or extracted glyphs)")
    p.add_argument("--style", choices=["block", "cursive"], default="block", help="handwriting template style")
    p.add_argument("-o", "--output", default="out.png", help="output file (.png, or .gif to animate)")
    p.add_argument("--make-template", metavar="PDF",
                   help="create ONE printable template (use --style block|cursive) and exit")
    p.add_argument("--make-templates", metavar="DIR",
                   help="create BOTH templates (block + cursive PDFs) in DIR and exit")
    p.add_argument("--size", type=float, default=1.0)
    p.add_argument("--ink", default="#1b1b3a")
    p.add_argument("--line-spacing", type=float, default=1.6)
    p.add_argument("--jitter", type=float, default=1.0)
    p.add_argument("--letter-spacing", type=float, default=1.0, help="0-3, 1 = natural")
    p.add_argument("--word-spacing", type=float, default=1.0, help="0-3, 1 = natural")
    p.add_argument("--paper", choices=["plain", "lined"], default="plain")
    p.add_argument("--width", type=int, default=1600)
    p.add_argument("--seed", type=int, default=None)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.make_templates:
        for path in make_both_templates(args.make_templates):
            print(f"Template written to {path}")
        return 0
    if args.make_template:
        print(f"Template written to {make_template(args.make_template, args.style)}")
        return 0
    if not args.text or not args.samples:
        print("error: give the text and --samples (or use --make-template)", file=sys.stderr)
        return 2
    writer = Writer.from_samples(args.samples, style=args.style)
    page = writer.write(args.text, size=args.size, ink=args.ink, line_spacing=args.line_spacing,
                        jitter=args.jitter, paper=args.paper,
                        letter_spacing=args.letter_spacing, word_spacing=args.word_spacing, width=args.width, seed=args.seed)
    out = page.animate(args.output) if args.output.lower().endswith(".gif") else page.save(args.output)
    print(f"Saved {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())