"""Make a local comparison sheet with transparency visible on checkerboard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "benchmarks" / "background"
MODELS = ("birefnet-dis", "ben2-base")
CELL = (420, 360)


def checker(size: tuple[int, int]) -> Image.Image:
    image = Image.new("RGBA", size, "#eeeeee")
    draw = ImageDraw.Draw(image)
    tile = 24
    for y in range(0, size[1], tile):
        for x in range(0, size[0], tile):
            if (x // tile + y // tile) % 2:
                draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill="#bbbbbb")
    return image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", choices=("cases.json", "isolated_cases.json"), default="cases.json")
    parser.add_argument("case_ids", nargs="*")
    args = parser.parse_args()
    manifest = json.loads((BENCHMARK / args.manifest).read_text(encoding="utf-8"))["cases"]
    selected = [case for case in manifest if not args.case_ids or case["id"] in args.case_ids]
    if not selected:
        raise ValueError("No matching cases")
    sheet = Image.new("RGB", (CELL[0] * 3, CELL[1] * len(selected)), "white")
    draw = ImageDraw.Draw(sheet)
    for row, case in enumerate(selected):
        group = "isolated" if args.manifest == "isolated_cases.json" else "scene"
        paths = [BENCHMARK / case["input"]] + [BENCHMARK / "output" / group / model / f"{case['id']}.png" for model in MODELS]
        for col, path in enumerate(paths):
            with Image.open(path) as opened:
                image = ImageOps.exif_transpose(opened).convert("RGBA")
            image = ImageOps.contain(image, (CELL[0], CELL[1] - 24), Image.Resampling.LANCZOS)
            background = checker((CELL[0], CELL[1] - 24)) if col else Image.new("RGBA", (CELL[0], CELL[1] - 24), "white")
            background.alpha_composite(image, ((background.width - image.width) // 2, (background.height - image.height) // 2))
            sheet.paste(background.convert("RGB"), (col * CELL[0], row * CELL[1] + 24))
            label = ("source", *MODELS)[col]
            draw.text((col * CELL[0] + 8, row * CELL[1] + 5), f"{case['id']} / {label}", fill="black")
    group = "isolated" if args.manifest == "isolated_cases.json" else "scene"
    destination = BENCHMARK / "output" / "comparisons" / group / ("comparison-" + "-".join(case["id"] for case in selected) + ".png")
    destination.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(destination)
    print(destination)


if __name__ == "__main__":
    main()
