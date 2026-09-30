"""Build a contact sheet thumbnail grid for all 200 flowers."""

from __future__ import annotations

import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "staging" / "flowers_200_2026-09-29"
TRANSPARENT_DIR = STAGING / "transparent_png"
CONTACT_SHEET = STAGING / "contact_sheet.jpg"


def make_contact_sheet():
    images = sorted(list(TRANSPARENT_DIR.glob("*.png")))
    if not images:
        raise ValueError("No images found in transparent_png")

    cols = 20
    rows = math.ceil(len(images) / cols)
    tile_size = 140
    text_h = 20
    cell_w = tile_size
    cell_h = tile_size + text_h

    sheet_w = cols * cell_w
    sheet_h = rows * cell_h

    # checkerboard background or light gray so transparent cutouts show clearly
    sheet = Image.new("RGB", (sheet_w, sheet_h), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)

    for idx, img_path in enumerate(images):
        r = idx // cols
        c = idx % cols
        x0 = c * cell_w
        y0 = r * cell_h

        with Image.open(img_path) as im:
            thumb = im.copy()
            thumb.thumbnail((tile_size - 8, tile_size - 8), Image.Resampling.LANCZOS)
            # paste onto white background box
            box = Image.new("RGBA", (tile_size, tile_size), (255, 255, 255, 255))
            tx = (tile_size - thumb.width) // 2
            ty = (tile_size - thumb.height) // 2
            box.paste(thumb, (tx, ty), thumb if thumb.mode == "RGBA" else None)
            sheet.paste(box.convert("RGB"), (x0, y0))

        # draw small label
        label = img_path.stem
        draw.text((x0 + 4, y0 + tile_size + 2), label, fill=(50, 50, 50))

    CONTACT_SHEET.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(CONTACT_SHEET, quality=90)
    print(f"Saved contact sheet to {CONTACT_SHEET} ({sheet_w}x{sheet_h})")


if __name__ == "__main__":
    make_contact_sheet()
