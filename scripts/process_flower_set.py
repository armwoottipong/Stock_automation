"""Process 200 flowers: stage generated images, upscale 4x, cutout to transparent PNG, and package."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

BATCH_ID = "34e178a82ddfc075"
STAGING_DIR = ROOT / "staging" / "flowers_200_2026-09-29"
MANIFEST_PATH = STAGING_DIR / "flowers_manifest.json"


def dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as img:
        img.verify()
    with Image.open(path) as img:
        return img.size


def stage_generated() -> dict:
    batch_dir = ROOT / "jobs" / "batches" / BATCH_ID
    plan_path = batch_dir / "batch_plan.json"
    if not plan_path.exists():
        raise FileNotFoundError(f"Plan not found: {plan_path}")

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    raw_dir = STAGING_DIR / "raw_1024"
    raw_dir.mkdir(parents=True, exist_ok=True)

    records = []
    for item in plan["items"]:
        item_id = item["id"]
        checkpoint_path = batch_dir / "items" / f"{item_id}.json"
        if not checkpoint_path.exists():
            raise RuntimeError(f"Item checkpoint missing for {item_id}")
        ckpt = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        if ckpt.get("status") != "completed":
            raise RuntimeError(f"Item {item_id} not completed: {ckpt.get('status')}")

        output_file = Path(ckpt["outputs"][0])
        staged_raw = raw_dir / f"{item_id}.png"
        if not staged_raw.exists():
            shutil.copy2(output_file, staged_raw)

        records.append({
            "id": item_id,
            "description": item["plan"]["request"]["prompt"],
            "seed": item["plan"]["request"]["seed"],
            "plan_id": item["plan"]["plan_id"],
            "raw_image": f"raw_1024/{item_id}.png",
        })

    manifest = {
        "created_at": datetime.now().isoformat(),
        "batch_id": BATCH_ID,
        "count": len(records),
        "records": records,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Staged {len(records)} generated raw images.")
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["stage_raw"])
    args = parser.parse_args()

    if args.action == "stage_raw":
        stage_generated()


if __name__ == "__main__":
    main()
