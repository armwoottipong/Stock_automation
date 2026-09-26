"""Publish compact, reproducible visual summaries of local benchmark evidence."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


ROOT = Path(__file__).resolve().parents[1]
BENCHMARKS = ROOT / "benchmarks"
DESTINATION = BENCHMARKS / "comparisons"


def save_jpeg(image: Image.Image, name: str, max_width: int = 1400) -> None:
    image = image.convert("RGB")
    if image.width > max_width:
        image = ImageOps.contain(image, (max_width, image.height * max_width // image.width), Image.Resampling.LANCZOS)
    DESTINATION.mkdir(parents=True, exist_ok=True)
    image.save(DESTINATION / name, quality=84, optimize=True, progressive=True)
    print(DESTINATION / name)


def generation() -> None:
    source = BENCHMARKS / "generation" / "2026-09-26" / "output" / "comparisons" / "contact_sheet.jpg"
    with Image.open(source) as image:
        save_jpeg(image, "generation-2026-09-26.jpg")


def background() -> None:
    base = BENCHMARKS / "background"
    cases = ("isolate_product_solid_02", "isolate_furniture_02", "isolate_glass_02")
    models = ("birefnet-dis", "ben2-base")
    cell = 360
    label_height = 28
    sheet = Image.new("RGB", (cell * 3, (cell + label_height) * len(cases)), "white")
    draw = ImageDraw.Draw(sheet)
    checker = Image.new("RGBA", (cell, cell), "#eeeeee")
    check_draw = ImageDraw.Draw(checker)
    for y in range(0, cell, 20):
        for x in range(0, cell, 20):
            if (x // 20 + y // 20) % 2:
                check_draw.rectangle((x, y, x + 19, y + 19), fill="#c5c5c5")
    for row, case in enumerate(cases):
        paths = (base / "input" / f"{case}.png",) + tuple(
            base / "output" / "isolated" / model / f"{case}.png" for model in models
        )
        for col, path in enumerate(paths):
            with Image.open(path) as image:
                preview = ImageOps.contain(image.convert("RGBA"), (cell, cell), Image.Resampling.LANCZOS)
            tile = Image.new("RGBA", (cell, cell), "white") if col == 0 else checker.copy()
            tile.alpha_composite(preview, ((cell - preview.width) // 2, (cell - preview.height) // 2))
            sheet.paste(tile.convert("RGB"), (col * cell, row * (cell + label_height)))
            label = ("source", *models)[col]
            draw.text((col * cell + 8, row * (cell + label_height) + cell + 6), f"{case} | {label}", fill="black")
    save_jpeg(sheet, "background-2026-09-25.jpg")


def upscale() -> None:
    base = BENCHMARKS / "upscale_x4" / "2026-09-26" / "sample_comparison"
    for name in ("center", "edge"):
        with Image.open(base / "comparisons" / f"{name}_contact.png") as image:
            save_jpeg(image, f"upscale-{name}-2026-09-26.jpg")


if __name__ == "__main__":
    generation()
    background()
    upscale()
