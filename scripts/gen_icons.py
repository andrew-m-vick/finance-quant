"""Generate opaque PNG app icons from the brand glyph.

iOS requires apple-touch-icon to be an opaque PNG — SVGs are not rendered
for the home-screen bookmark, and transparent backgrounds get filled with
black. So we bake the brand color into the PNG.

Three outputs:
  apple-touch-icon.png   180x180, edge-to-edge art (iOS masks corners itself)
  icon-192.png           192x192, manifest "any"
  icon-512.png           512x512, manifest "any"
  icon-maskable-512.png  512x512, safe-zone padded for "maskable" purpose
"""

import os

from PIL import Image, ImageDraw

BG = (27, 94, 32)  # #1b5e20
FG = (255, 255, 255)

OUT = os.path.join(os.path.dirname(__file__), "..", "static", "icons")
os.makedirs(OUT, exist_ok=True)


def draw_chart(img: Image.Image, inset: float) -> None:
    """Draw the up-and-to-the-right line chart glyph centered on img.

    inset is the fraction of image edge to leave as margin (0..0.5).
    """
    W, H = img.size
    m = int(min(W, H) * inset)
    # Chart points defined on a 0..1 grid, translated to the inset box.
    pts01 = [(0.00, 0.72), (0.25, 0.36), (0.47, 0.50), (0.75, 0.14), (1.00, 0.25)]
    box_w, box_h = W - 2 * m, H - 2 * m
    pts = [(m + int(x * box_w), m + int(y * box_h)) for x, y in pts01]

    draw = ImageDraw.Draw(img)
    line_w = max(6, int(min(W, H) * 0.08))
    draw.line(pts, fill=FG, width=line_w, joint="curve")
    # Endpoint dot.
    r = int(line_w * 0.9)
    cx, cy = pts[-1]
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=FG)
    # Rounded starts/ends (PIL line "joint=curve" handles joins but not caps).
    for cx, cy in (pts[0], pts[-1]):
        rr = line_w // 2
        draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=FG)


def make_icon(size: int, inset: float, filename: str) -> None:
    img = Image.new("RGB", (size, size), BG)
    draw_chart(img, inset)
    img.save(os.path.join(OUT, filename), "PNG", optimize=True)


# apple-touch-icon: iOS rounds corners itself; fill edge-to-edge with brand bg.
make_icon(180, inset=0.18, filename="apple-touch-icon.png")
# Regular PWA icons.
make_icon(192, inset=0.18, filename="icon-192.png")
make_icon(512, inset=0.18, filename="icon-512.png")
# Maskable: content within the safe zone (center ~60%). Use a larger inset.
make_icon(512, inset=0.25, filename="icon-maskable-512.png")

print("Wrote icons to", os.path.abspath(OUT))
