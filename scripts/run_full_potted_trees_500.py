"""End-to-end master runner for 500 potted trees set."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

BATCH_ID = "6b2e5fc9a1046a6d"
SET_ID = "potted_trees_500_2026-10-01_001"
STAGING_DIR = ROOT / "staging" / SET_ID
RAW_DIR = STAGING_DIR / "raw_1024"


def stage_raw_generated():
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

    (STAGING_DIR / "items_manifest.json").write_text(
        json.dumps({"set_id": SET_ID, "batch_id": BATCH_ID, "count": len(records), "records": records}, indent=2),
        encoding="utf-8"
    )
    print(f"Staged {len(records)} raw images to {RAW_DIR}.")


def main():
    print("==========================================================", flush=True)
    print(f"Starting 500 Potted Trees Master Pipeline: {SET_ID}", flush=True)
    print("==========================================================", flush=True)

    # 1. Run Generation Batch
    batch_plan_path = ROOT / "jobs" / "batches" / BATCH_ID / "batch_plan.json"
    cmd_gen = [
        sys.executable, str(ROOT / "scripts" / "batch.py"), "run",
        "--plan", str(batch_plan_path),
    ]
    t0 = time.perf_counter()
    print("Executing batch generation ...", flush=True)
    res_gen = subprocess.run(cmd_gen, cwd=ROOT)
    if res_gen.returncode != 0:
        raise RuntimeError("Generation batch failed")
    print(f"Generation batch finished in {time.perf_counter() - t0:.1f}s.", flush=True)

    # 2. Stage raw generated images
    stage_raw_generated()

    # 3. Ensure metadata catalog and CSV are generated
    cmd_meta = [sys.executable, str(ROOT / "scripts" / "prepare_potted_trees_metadata.py")]
    subprocess.run(cmd_meta, cwd=ROOT, check=True)

    # 4. Run 4K Pipeline (4x Upscale, Cutout, XMP, JPEG Companion, Packaging, Audit, Cleanup)
    cmd_pipeline = [
        sys.executable, str(ROOT / "scripts" / "run_4k_stock_pipeline.py"),
        "--set-id", SET_ID,
    ]
    subprocess.run(cmd_pipeline, cwd=ROOT, check=True)

    print("\n==========================================================", flush=True)
    print(f"ALL 500 POTTED TREES COMPLETED, PACKAGED AT 4K AND AUDITED!", flush=True)
    print("==========================================================", flush=True)


if __name__ == "__main__":
    main()
