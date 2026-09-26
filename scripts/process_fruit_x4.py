"""Resume the fruit set's default 4x pixel pass and opaque cutout pass."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "staging" / "fruit_isolates_2026-09-26"
MANIFEST = DATA / "x4_manifest.json"


def write_manifest(data: dict) -> None:
    temporary = MANIFEST.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(MANIFEST)


def dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        image.verify()
    with Image.open(path) as image:
        return image.size


def run_stage(stage: str) -> None:
    source = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {
        "created_at": source["created_at"],
        "count": len(source["records"]),
        "scale_from_original": 4,
        "upscale_model": "realesrgan-x4plus",
        "cutout_model": "birefnet-dis",
        "records": [{"name": row["name"], "original": row["original"]} for row in source["records"]],
    }
    target_key = "upscaled_x4" if stage == "upscale" else "cutout_x4"
    folder = DATA / target_key
    folder.mkdir(exist_ok=True)
    for index, (base, record) in enumerate(zip(source["records"], manifest["records"], strict=True), 1):
        if base["name"] != record["name"]:
            raise ValueError("Manifest record order changed")
        name = Path(base["upscaled"]).name
        input_path = DATA / (base["original"] if stage == "upscale" else f"upscaled_x4/{name}")
        target = folder / name
        input_size = dimensions(input_path)
        expected = tuple(value * 4 for value in input_size) if stage == "upscale" else input_size
        if target.exists() and dimensions(target) == expected and record.get(f"{stage}_job_id"):
            print(f"[{index}/25] {stage} skip {name}", flush=True)
            continue
        if stage == "upscale":
            command = [sys.executable, str(ROOT / "controller.py"), "upscale", "--input", str(input_path), "--scale", "4", "--model-id", "realesrgan-x4plus"]
        else:
            command = [str(ROOT / ".venv-comfyui" / "Scripts" / "python.exe"), str(ROOT / "scripts" / "remove_background.py"), "--input", str(input_path), "--subject", "opaque"]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f"{stage} failed for {name}: {result.stderr[-1000:]}")
        report = json.loads(result.stdout)
        if stage == "upscale":
            if report["status"] != "completed":
                raise RuntimeError(f"Upscale did not complete: {name}")
            rendered = Path(report["outputs"][0])
        else:
            if report["status"] != "manual_review_required" or not report["cutout_qc"]["passed"]:
                raise RuntimeError(f"Cutout QC failed: {name}")
            rendered = Path(report["output"])
        if dimensions(rendered) != expected:
            raise RuntimeError(f"Incorrect dimensions for {name}")
        shutil.copy2(rendered, target)
        record[target_key] = f"{target_key}/{name}"
        record[f"{stage}_job_id"] = report["job_id"]
        record[f"{stage}_qc_passed"] = True
        record["stock_review_required"] = True
        write_manifest(manifest)
        print(f"[{index}/25] {stage} done {name} {expected[0]}x{expected[1]}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("upscale", "cutout"))
    args = parser.parse_args()
    run_stage(args.stage)


if __name__ == "__main__":
    main()
