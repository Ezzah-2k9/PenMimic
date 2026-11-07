import sys
import cv2
import numpy as np
from penmimic import glyphs as G, template as T

gray = cv2.imread(sys.argv[1], cv2.IMREAD_GRAYSCALE)
print("image size:", gray.shape[::-1])
rect = G.rectify(gray)
norm = G.normalise_lighting(rect)
cv2.imwrite("debug_rectified.png", rect)
cv2.imwrite("debug_normalised.png", norm)
print("page number read:", G.read_page_number(norm))

x0, y0, _, _ = T.cell_box(0, 0)
x1, y1 = T.cell_box(T.ROWS_PER_PAGE - 1, T.VARIANTS - 1)[2:]
grid = norm[y0:y1, x0:x1]
print("darkest 0.5% of grid pixels:", int(np.percentile(grid, 0.5)), "(real ink should be well under 150)")
print("pixels under 150:", int((grid < 150).sum()), "| under 190:", int((grid < 190).sum()))

