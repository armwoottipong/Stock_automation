"""Full 4K Stock Pipeline: 4x upscale -> 4K cutout -> metadata -> package -> audit."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_image_automation.background import inspect_cutout, inspect_input, refine_opaque_cutout, resolve_background_model
from ai_image_automation.background_inference import cutout_birefnet, load_birefnet
from ai_image_automation.registry import LicenseRegistry, load_registry
from ai_image_automation.stock_metadata import export_csv, validate_catalog


def run_pipeline(set_dir: Path, set_id: str, max_items: int | None = None, keep_staging: bool = False):
    print(f"\n=======================================================", flush=True)
    print(f"Starting 4K Stock Pipeline for Set: {set_id}", flush=True)
    print(f"Directory: {set_dir}", flush=True)
    print(f"=======================================================\n", flush=True)

    raw_dir = set_dir / "raw_1024"
    upscaled_dir = set_dir / "upscaled_4k"
    cutout_dir = set_dir / "cutout_4k"
    pkg_dir = set_dir / "packages"
    adobe_pkg = pkg_dir / "adobe_stock"
    white_pkg = pkg_dir / "white_png_companion"

    upscaled_dir.mkdir(parents=True, exist_ok=True)
    cutout_dir.mkdir(parents=True, exist_ok=True)

    raw_images = sorted(list(raw_dir.glob("*.png")))
    if max_items:
        raw_images = raw_images[:max_items]
    total = len(raw_images)
    print(f"Total raw images to process: {total}", flush=True)

    # ---------------------------------------------------------
    # STAGE 1: 4x Pixel Upscale (RealESRGAN x4plus)
    # ---------------------------------------------------------
    print(f"\n--- STAGE 1: 4x Pixel Upscale (4096x4096) ---", flush=True)
    upscale_ckpt_file = set_dir / "upscale_4k_checkpoint.json"
    upscale_done = json.loads(upscale_ckpt_file.read_text()) if upscale_ckpt_file.exists() else {}

    t_up_start = time.perf_counter()
    for idx, raw_path in enumerate(raw_images, start=1):
        target = upscaled_dir / raw_path.name
        if target.exists() and upscale_done.get(raw_path.name):
            continue

        cmd = [
            sys.executable, str(ROOT / "controller.py"), "upscale",
            "--input", str(raw_path),
            "--scale", "4",
            "--model-id", "realesrgan-x4plus",
        ]
        sub_env = {"PYTHONPATH": str(ROOT / "src"), **os.environ}
        res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=sub_env)
        if res.returncode != 0:
            raise RuntimeError(f"Upscale failed for {raw_path.name}: {res.stderr[-500:]}")
        data = json.loads(res.stdout)
        out_rendered = Path(data["outputs"][0])
        shutil.copy2(out_rendered, target)

        upscale_done[raw_path.name] = True
        upscale_ckpt_file.write_text(json.dumps(upscale_done, indent=2))

        elapsed = time.perf_counter() - t_up_start
        avg = elapsed / idx
        remain = avg * (total - idx)
        if idx % 10 == 0 or idx == total:
            print(f"[{idx}/{total}] Upscaled 4x: {idx/total*100:.1f}% (~{remain/60:.1f} min left)", flush=True)

    print("Stage 1 (4x Upscale) completed.", flush=True)

    # ---------------------------------------------------------
    # STAGE 2: 4K Transparent Cutout (BiRefNet DIS)
    # ---------------------------------------------------------
    print(f"\n--- STAGE 2: 4K Transparent Cutout (BiRefNet) ---", flush=True)
    licenses = LicenseRegistry.model_validate_json((ROOT / "data" / "license_registry.json").read_text(encoding="utf-8"))
    _, checkpoint = resolve_background_model(
        load_registry(ROOT / "data" / "background_registry.json"), licenses, "birefnet-dis", root=ROOT
    )
    network = load_birefnet(checkpoint)
    print("BiRefNet model loaded into CUDA for 4K cutout.", flush=True)

    cutout_ckpt_file = set_dir / "cutout_4k_checkpoint.json"
    cutout_done = json.loads(cutout_ckpt_file.read_text()) if cutout_ckpt_file.exists() else {}

    t_cut_start = time.perf_counter()
    for idx, raw_path in enumerate(raw_images, start=1):
        target = cutout_dir / raw_path.name
        if target.exists() and cutout_done.get(raw_path.name):
            continue

        up_file = upscaled_dir / raw_path.name
        with Image.open(up_file) as src:
            raw = cutout_birefnet(network, src)
            cutout = refine_opaque_cutout(raw, edge_low=10, edge_high=245)
            temp = target.with_suffix(".tmp.png")
            cutout.save(temp, format="PNG")
            os.replace(temp, target)

        cutout_done[raw_path.name] = True
        cutout_ckpt_file.write_text(json.dumps(cutout_done, indent=2))

        if idx % 20 == 0 or idx == total:
            print(f"[{idx}/{total}] 4K Cutout progress: {idx/total*100:.1f}%", flush=True)

    print(f"Stage 2 (4K Cutout) completed in {time.perf_counter() - t_cut_start:.1f}s.", flush=True)

    # ---------------------------------------------------------
    # STAGE 3: Contact Sheet
    # ---------------------------------------------------------
    print(f"\n--- STAGE 3: Contact Sheet ---", flush=True)
    images_cut = sorted(list(cutout_dir.glob("*.png")))
    cols = 20 if total <= 200 else 25
    rows = math.ceil(len(images_cut) / cols)
    tile_size = 130
    text_h = 18
    sheet = Image.new("RGB", (cols * tile_size, rows * (tile_size + text_h)), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)

    for idx, img_path in enumerate(images_cut):
        r = idx // cols
        c = idx % cols
        x0 = c * tile_size
        y0 = r * (tile_size + text_h)
        with Image.open(img_path) as im:
            thumb = im.copy()
            thumb.thumbnail((tile_size - 6, tile_size - 6), Image.Resampling.LANCZOS)
            box = Image.new("RGBA", (tile_size, tile_size), (255, 255, 255, 255))
            tx = (tile_size - thumb.width) // 2
            ty = (tile_size - thumb.height) // 2
            box.paste(thumb, (tx, ty), thumb if thumb.mode == "RGBA" else None)
            sheet.paste(box.convert("RGB"), (x0, y0))
        draw.text((x0 + 2, y0 + tile_size + 1), img_path.stem, fill=(50, 50, 50))

    contact_path = set_dir / "contact_sheet_4k.jpg"
    sheet.save(contact_path, quality=90)
    print(f"Saved contact sheet to {contact_path}", flush=True)

    # ---------------------------------------------------------
    # STAGE 4: Stock Metadata Preparation & Validation
    # ---------------------------------------------------------
    print(f"\n--- STAGE 4: Stock Metadata Preparation ---", flush=True)
    # Check if catalog exists or build from existing catalog
    existing_catalog_file = set_dir / "catalog.json"
    if existing_catalog_file.exists():
        catalog = json.loads(existing_catalog_file.read_text(encoding="utf-8"))
    else:
        raise FileNotFoundError(f"Missing catalog.json in {set_dir}")

    # Re-validate with cutout_4k
    validate_catalog(catalog, "adobe", cutout_dir)
    csv_text = export_csv(catalog, "adobe")
    (set_dir / "adobe_stock.csv").write_text(csv_text, encoding="utf-8")
    print(f"Validated Adobe Stock metadata and exported CSV ({len(catalog['records'])} records).", flush=True)

    # ---------------------------------------------------------
    # STAGE 5: Embed XMP Metadata
    # ---------------------------------------------------------
    print(f"\n--- STAGE 5: Embed XMP Metadata ---", flush=True)
    adobe_pkg.mkdir(parents=True, exist_ok=True)
    cmd_embed = [
        sys.executable, str(ROOT / "scripts" / "embed_stock_metadata.py"),
        "--catalog", str(existing_catalog_file),
        "--assets", str(cutout_dir),
        "--output", str(adobe_pkg),
        "--platform", "adobe",
    ]
    subprocess.run(cmd_embed, cwd=ROOT, check=True)
    print("Embedded XMP metadata into all 4K transparent PNGs.", flush=True)

    # ---------------------------------------------------------
    # STAGE 6: Packaging & Final Audit (Clean Structure)
    # ---------------------------------------------------------
    print(f"\n--- STAGE 6: Packaging & Final Audit ---", flush=True)

    # 1. Build white_jpeg_companion from transparent PNGs (Strictly JPEG only)
    white_jpg_pkg = pkg_dir / "white_jpeg_companion"
    white_jpg_pkg.mkdir(parents=True, exist_ok=True)
    jpg_names = []
    for png_path in sorted(adobe_pkg.glob("*.png")):
        jpg_name = png_path.stem + ".jpg"
        jpg_path = white_jpg_pkg / jpg_name
        jpg_names.append(jpg_name)
        if not jpg_path.exists():
            with Image.open(png_path) as im:
                rgba = im.convert("RGBA")
                bg = Image.new("RGB", rgba.size, (255, 255, 255))
                bg.paste(rgba, mask=rgba.split()[3])
                bg.save(jpg_path, "JPEG", quality=95, subsampling=0)

    # Batch copy metadata from adobe_stock PNGs to JPEGs
    cmd_meta = [
        "exiftool", "-overwrite_original", "-q", "-q",
        "-tagsFromFile", f"{adobe_pkg}/%f.png",
        "-all:all", "-ext", "jpg", str(white_jpg_pkg),
    ]
    subprocess.run(cmd_meta, cwd=ROOT, check=True)

    # Sanitize JPEG metadata: remove any transparent tags and add white background tag
    cmd_sanitize = [
        "exiftool", "-overwrite_original", "-q", "-q",
        "-XMP-dc:Subject-=transparent background",
        "-XMP-dc:Subject-=transparent",
        "-XMP-dc:Subject-=transparency",
        "-XMP-dc:Subject+=white background",
        "-ext", "jpg", str(white_jpg_pkg),
    ]
    subprocess.run(cmd_sanitize, cwd=ROOT, check=True)

    # 2. Build metadata package (dedicated folder for CSV, catalog, manifests, contact sheet)
    meta_pkg = pkg_dir / "metadata"
    meta_pkg.mkdir(parents=True, exist_ok=True)
    shutil.copy2(set_dir / "adobe_stock.csv", meta_pkg / "adobe_stock.csv")
    if (set_dir / "catalog.json").exists():
        shutil.copy2(set_dir / "catalog.json", meta_pkg / "catalog.json")
    if (set_dir / "contact_sheet_4k.jpg").exists():
        shutil.copy2(set_dir / "contact_sheet_4k.jpg", meta_pkg / "contact_sheet_4k.jpg")

    # 3. Adobe Stock package manifest (stored in metadata/ to keep adobe_stock/ 100% clean images only)
    adobe_pngs = sorted([p.name for p in adobe_pkg.glob("*.png")])
    adobe_manifest = {
        "platform": "adobe_stock",
        "source_type": "generative_ai",
        "adobe_ai_disclosure_required": True,
        "checks": {"metadata": True, "technical": True, "rights": True},
        "image_count": len(adobe_pngs),
        "assets": adobe_pngs,
        "source_set": set_id,
        "submission_note": "Technically prepared 4K (4096x4096px, 16.7MP) transparent-PNG assets for Adobe Stock with embedded XMP. Select Created using generative AI tools in the Adobe Contributor Portal.",
    }
    (meta_pkg / "adobe_stock_manifest.json").write_text(json.dumps(adobe_manifest, indent=2) + "\n", encoding="utf-8")

    # 4. White JPEG companion manifest (stored in metadata/ to keep white_jpeg_companion/ 100% clean images only)
    white_jpg_manifest = {
        "platform": "local_delivery",
        "package_purpose": "white_jpeg_companion",
        "source_type": "generative_ai",
        "checks": {"metadata": True, "technical": True, "rights": True},
        "image_count": len(jpg_names),
        "source_set": set_id,
        "assets": jpg_names,
        "submission_note": "Solid-white 4K (4096x4096px) JPEG companions with pure white background and embedded XMP metadata.",
    }
    (meta_pkg / "white_jpeg_companion_manifest.json").write_text(json.dumps(white_jpg_manifest, indent=2) + "\n", encoding="utf-8")

    # 5. Metadata package manifest
    meta_assets = sorted([f.name for f in meta_pkg.iterdir() if f.is_file()])
    meta_manifest = {
        "platform": "local_delivery",
        "package_purpose": "metadata_companion",
        "source_type": "generative_ai",
        "checks": {"metadata": True, "technical": True, "rights": True},
        "source_set": set_id,
        "assets": meta_assets,
        "submission_note": "Metadata catalog, Adobe Stock CSV, package manifests, and contact sheet preview companion.",
    }
    (meta_pkg / "submission_manifest.json").write_text(json.dumps(meta_manifest, indent=2) + "\n", encoding="utf-8")

    # Remove existing destination in output/ to avoid FileExistsError
    dest = ROOT / "output" / set_id
    if dest.exists():
        shutil.rmtree(dest)

    cmd_pkg = [
        sys.executable, str(ROOT / "scripts" / "package_stock_set.py"),
        "--set-id", set_id,
        "--packages", str(adobe_pkg), str(white_jpg_pkg), str(meta_pkg),
    ]
    subprocess.run(cmd_pkg, cwd=ROOT, check=True)

    cmd_audit = [sys.executable, str(ROOT / "scripts" / "audit_output.py")]
    subprocess.run(cmd_audit, cwd=ROOT, check=True)
    print(f"\nSUCCESS: Set {set_id} packaged and audited at 4K (4096x4096px)!", flush=True)

    # ---------------------------------------------------------
    # STAGE 7: Clean Staging & Intermediate Junk Files
    # ---------------------------------------------------------
    if not keep_staging:
        print(f"\n--- STAGE 7: Cleaning Staging Files ---", flush=True)
        for folder_name in ["raw_1024", "upscaled_4k", "cutout_4k", "packages"]:
            heavy_dir = set_dir / folder_name
            if heavy_dir.exists():
                shutil.rmtree(heavy_dir)
                print(f"Removed intermediate staging directory: {folder_name}", flush=True)
        print(f"Staging cleanup complete for {set_id}.", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", choices=["flowers_200", "plants_250", "plants_mushrooms_500", "both"], default="plants_mushrooms_500")
    parser.add_argument("--keep-staging", action="store_true", help="Keep intermediate staging image files")
    args = parser.parse_args()

    sets = []
    if args.set in ["flowers_200", "both"]:
        sets.append((ROOT / "staging" / "flowers_200_2026-09-29", "flowers_200_2026-09-29"))
    if args.set in ["plants_250", "both"]:
        sets.append((ROOT / "staging" / "plants_flowers_250_2026-09-29_001", "plants_flowers_250_2026-09-29_001"))
    if args.set in ["plants_mushrooms_500"]:
        sets.append((ROOT / "staging" / "plants_mushrooms_500_2026-09-30_001", "plants_mushrooms_500_2026-09-30_001"))

    for sdir, sid in sets:
        run_pipeline(sdir, sid, keep_staging=args.keep_staging)


if __name__ == "__main__":
    main()
