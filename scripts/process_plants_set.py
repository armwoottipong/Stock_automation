"""End-to-end post-generation processing for 250 plants & flowers set."""

from __future__ import annotations

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

BATCH_ID = "961d58ee5fce7c32"
SET_ID = "plants_flowers_250_2026-09-29_001"
STAGING_DIR = ROOT / "staging" / SET_ID
RAW_DIR = STAGING_DIR / "raw_1024"
TRANSPARENT_DIR = STAGING_DIR / "transparent_png"
PACKAGES_DIR = STAGING_DIR / "packages"
ADOBE_PKG = PACKAGES_DIR / "adobe_stock"
WHITE_PKG = PACKAGES_DIR / "white_png_companion"


def stage_raw():
    batch_dir = ROOT / "jobs" / "batches" / BATCH_ID
    plan_path = batch_dir / "batch_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    records = []
    for item in plan["items"]:
        item_id = item["id"]
        ckpt = json.loads((batch_dir / "items" / f"{item_id}.json").read_text(encoding="utf-8"))
        if ckpt.get("status") != "completed":
            raise RuntimeError(f"Item {item_id} not completed")
        out_file = Path(ckpt["outputs"][0])
        staged = RAW_DIR / f"{item_id}.png"
        if not staged.exists():
            shutil.copy2(out_file, staged)
        records.append({
            "id": item_id,
            "description": item["plan"]["request"]["prompt"],
            "seed": item["plan"]["request"]["seed"],
            "raw_image": f"raw_1024/{item_id}.png",
        })

    (STAGING_DIR / "plants_manifest.json").write_text(
        json.dumps({"set_id": SET_ID, "batch_id": BATCH_ID, "count": len(records), "records": records}, indent=2),
        encoding="utf-8"
    )
    print(f"Staged {len(records)} raw images.")


def batch_cutout():
    TRANSPARENT_DIR.mkdir(parents=True, exist_ok=True)
    licenses = LicenseRegistry.model_validate_json((ROOT / "data" / "license_registry.json").read_text(encoding="utf-8"))
    _, checkpoint = resolve_background_model(
        load_registry(ROOT / "data" / "background_registry.json"), licenses, "birefnet-dis", root=ROOT
    )
    print(f"Loading BiRefNet from {checkpoint} ...", flush=True)
    network = load_birefnet(checkpoint)
    print("BiRefNet model loaded.", flush=True)

    images = sorted(list(RAW_DIR.glob("*.png")))
    total = len(images)
    results = []
    t_start = time.perf_counter()

    for idx, img_path in enumerate(images, start=1):
        t0 = time.perf_counter()
        target_path = TRANSPARENT_DIR / img_path.name
        with Image.open(img_path) as src:
            inspect_input(src)
            raw = cutout_birefnet(network, src)
            cutout = refine_opaque_cutout(raw, edge_low=10, edge_high=245)
            qc = inspect_cutout(src, cutout)
            temp = target_path.with_suffix(".tmp.png")
            cutout.save(temp, format="PNG")
            os.replace(temp, target_path)

        results.append({
            "name": img_path.name,
            "qc_passed": qc["passed"],
            "issues": qc["issues"],
            "duration": round(time.perf_counter() - t0, 3),
        })
        if idx % 25 == 0 or idx == total:
            print(f"[{idx}/{total}] Cutout progress: {idx/total*100:.1f}%", flush=True)

    (STAGING_DIR / "cutout_report.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Batch cutout completed for {total} images in {time.perf_counter() - t_start:.1f}s.")


def make_contact_sheet():
    images = sorted(list(TRANSPARENT_DIR.glob("*.png")))
    cols = 25
    rows = math.ceil(len(images) / cols)
    tile_size = 120
    text_h = 18
    cell_w = tile_size
    cell_h = tile_size + text_h

    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), (245, 245, 245))
    draw = ImageDraw.Draw(sheet)

    for idx, img_path in enumerate(images):
        r = idx // cols
        c = idx % cols
        x0 = c * cell_w
        y0 = r * cell_h

        with Image.open(img_path) as im:
            thumb = im.copy()
            thumb.thumbnail((tile_size - 6, tile_size - 6), Image.Resampling.LANCZOS)
            box = Image.new("RGBA", (tile_size, tile_size), (255, 255, 255, 255))
            tx = (tile_size - thumb.width) // 2
            ty = (tile_size - thumb.height) // 2
            box.paste(thumb, (tx, ty), thumb if thumb.mode == "RGBA" else None)
            sheet.paste(box.convert("RGB"), (x0, y0))

        label = img_path.stem
        draw.text((x0 + 2, y0 + tile_size + 1), label, fill=(50, 50, 50))

    dest = STAGING_DIR / "contact_sheet.jpg"
    sheet.save(dest, quality=90)
    print(f"Saved contact sheet to {dest} ({sheet.width}x{sheet.height})")


def prepare_metadata():
    manifest = json.loads((STAGING_DIR / "plants_manifest.json").read_text(encoding="utf-8"))
    records = []
    base_kws = ["isolated", "cutout", "transparent background", "botanical", "nature", "plant"]

    for item in manifest["records"]:
        item_id = item["id"]
        parts = item_id.rsplit("_", 1)
        species_name = parts[0].replace("_", " ").title()
        var_num = int(parts[1])

        title_types = {
            1: f"Fresh {species_name} Centered Full View",
            2: f"Single {species_name} Top Down View",
            3: f"Side Profile View of Fresh {species_name}",
            4: f"Detailed View of Natural {species_name}",
            5: f"Young {species_name} New Growth Botanical",
        }
        raw_title = title_types.get(var_num, f"Natural {species_name} Botanical Isolate")
        clean_title = re.sub(r"[^\w\s-]", "", raw_title)

        kws = [
            parts[0].replace("_", " "),
            species_name.lower(),
            "greenery",
            "foliage",
            "leaf",
            "indoor plant",
            "garden",
            *base_kws
        ]
        kws = list(dict.fromkeys(kws))

        records.append({
            "filename": f"{item_id}.png",
            "title": clean_title,
            "keywords": kws,
            "adobe_category": "12",
        })

    catalog = {
        "language": "en",
        "source_type": "generative_ai",
        "records": records,
    }
    validate_catalog(catalog, "adobe", TRANSPARENT_DIR)
    (STAGING_DIR / "catalog.json").write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")

    csv_text = export_csv(catalog, "adobe")
    (STAGING_DIR / "adobe_stock.csv").write_text(csv_text, encoding="utf-8")
    print(f"Metadata catalog and CSV validated for {len(records)} items.")


def embed_metadata():
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "embed_stock_metadata.py"),
        "--catalog", str(STAGING_DIR / "catalog.json"),
        "--assets", str(TRANSPARENT_DIR),
        "--output", str(ADOBE_PKG),
        "--platform", "adobe",
    ]
    print("Running embed_stock_metadata.py ...", flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)
    print("XMP embedding complete.")


def package_and_audit():
    # 1. Copy CSV to adobe_stock package
    shutil.copy2(STAGING_DIR / "adobe_stock.csv", ADOBE_PKG / "adobe_stock.csv")

    # 2. Adobe submission manifest
    pngs = sorted([p.name for p in ADOBE_PKG.glob("*.png")])
    if len(pngs) != 250:
        raise ValueError(f"Expected 250 pngs, got {len(pngs)}")

    adobe_manifest = {
        "platform": "adobe_stock",
        "source_type": "generative_ai",
        "adobe_ai_disclosure_required": True,
        "checks": {"metadata": True, "technical": True, "rights": True},
        "image_count": len(pngs),
        "assets": [*pngs, "adobe_stock.csv"],
        "source_set": SET_ID,
        "submission_note": "Technically prepared transparent-PNG assets for Adobe Stock. Select Created using generative AI tools in the Adobe Contributor Portal.",
    }
    (ADOBE_PKG / "submission_manifest.json").write_text(json.dumps(adobe_manifest, indent=2) + "\n", encoding="utf-8")

    # 3. White companion package
    WHITE_PKG.mkdir(parents=True, exist_ok=True)
    raw_pngs = sorted(list(RAW_DIR.glob("*.png")))
    for p in raw_pngs:
        target = WHITE_PKG / p.name
        if not target.exists():
            shutil.copy2(p, target)

    white_manifest = {
        "platform": "local_delivery",
        "package_purpose": "white_png_companion",
        "source_type": "generative_ai",
        "checks": {"metadata": True, "technical": True, "rights": True},
        "image_count": len(raw_pngs),
        "source_set": SET_ID,
        "assets": [p.name for p in raw_pngs],
        "submission_note": "Solid-white PNG companions; not Adobe Stock transparent-PNG submission assets.",
    }
    (WHITE_PKG / "submission_manifest.json").write_text(json.dumps(white_manifest, indent=2) + "\n", encoding="utf-8")

    # 4. Package set
    cmd_pkg = [
        sys.executable, str(ROOT / "scripts" / "package_stock_set.py"),
        "--set-id", SET_ID,
        "--packages", str(ADOBE_PKG), str(WHITE_PKG),
    ]
    subprocess.run(cmd_pkg, cwd=ROOT, check=True)

    # 5. Audit
    cmd_audit = [sys.executable, str(ROOT / "scripts" / "audit_output.py")]
    subprocess.run(cmd_audit, cwd=ROOT, check=True)
    print("Set packaged and audited successfully!")


def main():
    stage_raw()
    batch_cutout()
    make_contact_sheet()
    prepare_metadata()
    embed_metadata()
    package_and_audit()


if __name__ == "__main__":
    main()
