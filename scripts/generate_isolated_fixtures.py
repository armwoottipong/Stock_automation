"""Execute the frozen isolate fixture plan through the existing controller."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image
from PIL import ImageStat


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "benchmarks" / "background"
PLAN = BENCHMARK / "isolated_generation.json"


def main() -> None:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    destination_dir = BENCHMARK / "input"
    destination_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": 1, "policy": "clean_cutout_remove_original_shadow_and_floor_reflection", "cases": []}
    for case in plan["cases"]:
        destination = destination_dir / f"{case['id']}.png"
        if destination.exists():
            print(f"Reusing existing {destination.name}", flush=True)
        else:
            command = [
                sys.executable, str(ROOT / "controller.py"), "generate",
                "--model-id", plan["checkpoint_id"],
                "--prompt", case["prompt"],
                "--negative-prompt", plan["negative_prompt"],
                "--width", str(plan["width"]),
                "--height", str(plan["height"]),
                "--steps", str(plan["steps"]),
                "--cfg", str(plan["cfg"]),
                "--sampler-name", plan["sampler_name"],
                "--scheduler", plan["scheduler"],
                "--seed", str(case["seed"]),
            ]
            completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
            if completed.returncode:
                raise RuntimeError(f"Generation failed for {case['id']}: {completed.stderr.strip()}")
            record = json.loads(completed.stdout)
            outputs = record["outputs"]
            if len(outputs) != 1:
                raise RuntimeError(f"Expected one output for {case['id']}, got {len(outputs)}")
            shutil.copyfile(outputs[0], destination)
            print(f"Generated {case['id']} from job {record['job_id']}", flush=True)
        with Image.open(destination) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            corner = rgb.crop((0, 0, min(80, width), min(80, height)))
            stats = ImageStat.Stat(corner)
            corner_mean = [round(value, 1) for value in stats.mean]
            corner_stddev = [round(value, 1) for value in stats.stddev]
            near_white_corner = min(corner_mean) >= 245 and max(corner_stddev) <= 5
        manifest["cases"].append({
            "id": case["id"],
            "category": case["category"],
            "input": f"input/{destination.name}",
            "source": "local SDXL generation from isolated_generation.json",
            "license": "CreativeML Open RAIL++-M source checkpoint",
            "author": "local SDXL workflow",
            "requested_background": case["background"],
            "corner_mean_rgb": corner_mean,
            "corner_stddev_rgb": corner_stddev,
            "near_white_corner": near_white_corner,
            "seed": case["seed"],
        })
        (BENCHMARK / "isolated_cases.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
