"""Batch cutout for 200 flower images using BiRefNet DIS."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_image_automation.background import (
    inspect_cutout, inspect_input, refine_opaque_cutout, resolve_background_model, sha256_file
)
from ai_image_automation.background_inference import cutout_birefnet, load_birefnet
from ai_image_automation.registry import LicenseRegistry, load_registry

STAGING = ROOT / "staging" / "flowers_200_2026-09-29"
RAW_DIR = STAGING / "raw_1024"
OUT_DIR = STAGING / "transparent_png"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    licenses = LicenseRegistry.model_validate_json((ROOT / "data" / "license_registry.json").read_text(encoding="utf-8"))
    model_record, checkpoint = resolve_background_model(
        load_registry(ROOT / "data" / "background_registry.json"), licenses, "birefnet-dis", root=ROOT
    )

    print(f"Loading BiRefNet checkpoint from {checkpoint} ...", flush=True)
    network = load_birefnet(checkpoint)
    print("BiRefNet model loaded into CUDA.", flush=True)

    images = sorted(list(RAW_DIR.glob("*.png")))
    total = len(images)
    print(f"Found {total} images to process.", flush=True)

    results = []
    start_time = time.perf_counter()

    for idx, img_path in enumerate(images, start=1):
        t0 = time.perf_counter()
        target_path = OUT_DIR / img_path.name
        
        with Image.open(img_path) as source:
            input_check = inspect_input(source)
            raw = cutout_birefnet(network, source)
            cutout = refine_opaque_cutout(raw, edge_low=10, edge_high=245)
            qc = inspect_cutout(source, cutout)
            
            temp_path = target_path.with_suffix(".tmp.png")
            cutout.save(temp_path, format="PNG")
            os.replace(temp_path, target_path)

        elapsed = time.perf_counter() - t0
        passed = qc["passed"]
        results.append({
            "name": img_path.name,
            "output": str(target_path),
            "qc_passed": passed,
            "issues": qc["issues"],
            "foreground_fraction": qc["foreground_fraction"],
            "duration_seconds": round(elapsed, 3),
        })

        if idx % 10 == 0 or idx == total:
            overall_elapsed = time.perf_counter() - start_time
            avg = overall_elapsed / idx
            remain = avg * (total - idx)
            print(f"[{idx}/{total}] Cutout progress: {idx/total*100:.1f}% (avg {avg:.2f}s/img, ~{remain:.0f}s left)", flush=True)

    report_path = STAGING / "cutout_report.json"
    report_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    
    passed_count = sum(1 for r in results if r["qc_passed"])
    print(f"Finished batch cutout: {total} images processed. Total elapsed: {time.perf_counter() - start_time:.1f}s")
    print(f"Strict QC passed: {passed_count}/{total}")


if __name__ == "__main__":
    main()
