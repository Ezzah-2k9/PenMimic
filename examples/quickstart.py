import argparse
from penmimic import Writer

parser = argparse.ArgumentParser(description="Render text from your handwriting samples.")
parser.add_argument("--samples", default="my_samples", help="folder containing filled template page images")
parser.add_argument("--style", choices=["block", "cursive"], default="block")
parser.add_argument("--output", default="handwriting.png")
args = parser.parse_args()

writer = Writer.from_samples(args.samples, style=args.style)
writer.write("Hello World.\nThis is PenMimic.", size=0.9, jitter=0.25, seed=42).save(args.output)
print(f"Saved {args.output}")


