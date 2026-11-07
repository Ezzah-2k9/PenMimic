import pathlib
import pymupdf  # installed by "pip install pymupdf"

folder = pathlib.Path("my_samples")
for pdf in sorted(folder.glob("*.pdf")):
    doc = pymupdf.open(pdf)
    for i, page in enumerate(doc):
        out = folder / f"{pdf.stem}_p{i + 1}.png"
        page.get_pixmap(dpi=150).save(out)
        print("saved", out)