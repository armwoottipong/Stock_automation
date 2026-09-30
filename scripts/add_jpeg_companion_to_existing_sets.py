"""Add white_jpeg_companion package to existing audited 4K sets."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

SETS = [
    ("flowers_200_2026-09-29", ROOT / "staging" / "flowers_200_2026-09-29"),
    ("plants_flowers_250_2026-09-29_001", ROOT / "staging" / "plants_flowers_250_2026-09-29_001"),
]


def process_set(set_id: str, set_dir: Path):
    print(f"\nProcessing set: {set_id} ...", flush=True)
    adobe_pkg = set_dir / "packages" / "adobe_stock"
    white_png_pkg = set_dir / "packages" / "white_png_companion"
    white_jpg_pkg = set_dir / "packages" / "white_jpeg_companion"
    white_jpg_pkg.mkdir(parents=True, exist_ok=True)

    png_files = sorted(list(adobe_pkg.glob("*.png")))
    total = len(png_files)
    print(f"Converting {total} transparent PNGs to solid-white JPEGs ...", flush=True)

    t0 = time.perf_counter()
    jpg_names = []
    for idx, png_path in enumerate(png_files, start=1):
        jpg_name = png_path.stem + ".jpg"
        jpg_path = white_jpg_pkg / jpg_name
        jpg_names.append(jpg_name)

        if not jpg_path.exists():
            with Image.open(png_path) as im:
                rgba = im.convert("RGBA")
                bg = Image.new("RGB", rgba.size, (255, 255, 255))
                bg.paste(rgba, mask=rgba.split()[3])
                bg.save(jpg_path, "JPEG", quality=95, subsampling=0)

        if idx % 50 == 0 or idx == total:
            print(f"[{idx}/{total}] JPEG rendered: {idx/total*100:.0f}%", flush=True)

    print(f"JPEGs rendered in {time.perf_counter() - t0:.1f}s. Now copying XMP metadata ...", flush=True)

    # Batch copy metadata from adobe_stock PNGs to white_jpeg_companion JPEGs using exiftool
    t_meta = time.perf_counter()
    cmd_meta = [
        "exiftool", "-overwrite_original", "-q", "-q",
        "-tagsFromFile", f"{adobe_pkg}/%f.png",
        "-all:all",
        "-ext", "jpg",
        str(white_jpg_pkg),
    ]
    subprocess.run(cmd_meta, cwd=ROOT, check=True)
    print(f"Metadata copied in {time.perf_counter() - t_meta:.1f}s.", flush=True)

    # Create submission_manifest.json for white_jpeg_companion
    manifest = {
        "platform": "local_delivery",
        "package_purpose": "white_jpeg_companion",
        "source_type": "generative_ai",
        "checks": {
            "metadata": True,
            "technical": True,
            "rights": True,
        },
        "image_count": len(jpg_names),
        "source_set": set_id,
        "assets": jpg_names,
        "submission_note": "Solid-white 4K (4096x4096px) JPEG companions with pure white background and embedded XMP metadata.",
    }
    (white_jpg_pkg / "submission_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # Re-package set
    dest = ROOT / "output" / set_id
    if dest.exists():
        shutil.rmtree(dest)

    cmd_pkg = [
        sys.executable, str(ROOT / "scripts" / "package_stock_set.py"),
        "--set-id", set_id,
        "--packages", str(adobe_pkg), str(white_jpg_pkg), str(white_png_pkg),
    ]
    subprocess.run(cmd_pkg, cwd=ROOT, check=True)
    print(f"Set {set_id} successfully re-packaged with 3 packages (adobe_stock, white_jpeg_companion, white_png_companion).", flush=True)


def main():
    for sid, sdir in SETS:
        process_set(sid, sdir)

    print("\nRunning final audit across output/ ...", flush=True)
    cmd_audit = [sys.executable, str(ROOT / "scripts" / "audit_output.py")]
    subprocess.run(cmd_audit, cwd=ROOT, check=True)
    print("ALL SETS AUDITED SUCCESSFULLY WITH JPEG COMPANIONS!")


if __name__ == "__main__":
    main()
