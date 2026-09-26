"""Build a side-by-side contact sheet from a frozen generation benchmark."""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    run = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    cases = json.loads((run_dir / run["cases"]).read_text(encoding="utf-8"))["cases"]
    models = list(run["models"])
    tile = 360
    label_height = 32
    sheet = Image.new("RGB", (tile * len(models), (tile + label_height) * len(cases)), "white")
    draw = ImageDraw.Draw(sheet)
    for row, case in enumerate(cases):
        for col, model in enumerate(models):
            path = run_dir / "output" / model / f"{case['id']}.png"
            if not path.is_file():
                raise FileNotFoundError(path)
            with Image.open(path) as source:
                preview = source.convert("RGB")
                preview.thumbnail((tile, tile))
                x = col * tile + (tile - preview.width) // 2
                y = row * (tile + label_height) + (tile - preview.height) // 2
                sheet.paste(preview, (x, y))
            draw.text((col * tile + 8, row * (tile + label_height) + tile + 8),
                      f"{case['id']} | {model}", fill="black")
    destination = run_dir / "output" / "comparisons" / "contact_sheet.jpg"
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination, quality=92)
    print(destination)


if __name__ == "__main__":
    main()
