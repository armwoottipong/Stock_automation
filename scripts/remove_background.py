"""Run the frozen Phase 6 opaque cutout workflow in the CUDA Python environment."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_image_automation.background import (  # noqa: E402
    BackgroundRequest, inspect_cutout, inspect_input, refine_opaque_cutout,
    resolve_background_model, sha256_file,
)
from ai_image_automation.background_inference import cutout_birefnet, load_birefnet  # noqa: E402
from ai_image_automation.quality.stock_policy import STOCK_REVIEW_CHECKS  # noqa: E402
from ai_image_automation.registry import LicenseRegistry, load_registry  # noqa: E402


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def run(request: BackgroundRequest, jobs_dir: Path) -> dict:
    source_path = request.input.resolve()
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    with Image.open(source_path) as original:
        original.load()
        input_check = inspect_input(original)
        image_size = list(original.size)
    licenses = LicenseRegistry.model_validate_json((ROOT / "data" / "license_registry.json").read_text(encoding="utf-8"))
    model, checkpoint = resolve_background_model(
        load_registry(ROOT / "data" / "background_registry.json"), licenses, request.model_id, root=ROOT,
    )
    if model.id != "birefnet-dis":
        raise ValueError(f"No Phase 6 inference adapter for {model.id}")
    frozen = {
        **request.model_dump(mode="json"),
        "input": str(source_path),
        "input_sha256": sha256_file(source_path),
        "input_size": image_size,
        "model_revision": model.version,
        "model_sha256": model.sha256,
        "policy": "clean_cutout_remove_original_shadow_and_floor_reflection",
    }
    canonical = json.dumps(frozen, sort_keys=True, separators=(",", ":"))
    job_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
    job_dir = jobs_dir / job_id
    request_file = job_dir / "request.json"
    if request_file.exists() and json.loads(request_file.read_text(encoding="utf-8")) != frozen:
        raise ValueError(f"Frozen request changed for job {job_id}")
    write_json(request_file, frozen)
    output = job_dir / "output" / "cutout.png"
    qc_file = job_dir / "qc.json"
    if request.subject != "opaque":
        report = {
            "job_id": job_id, "status": "manual_review_required", "output": None,
            "reason": "transparent_subject_has_no_automatic_cutout_path",
            "input_check": input_check,
            "stock_review_required": list(STOCK_REVIEW_CHECKS),
        }
        write_json(qc_file, report)
        return report
    if output.is_file() and qc_file.is_file():
        report = json.loads(qc_file.read_text(encoding="utf-8"))
        if report.get("output_sha256") == sha256_file(output):
            return report
        raise ValueError(f"Existing cutout changed for job {job_id}")

    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for the registered BiRefNet inference")
    started = time.perf_counter()
    network = load_birefnet(checkpoint)
    torch.cuda.reset_peak_memory_stats()
    with Image.open(source_path) as source:
        raw = cutout_birefnet(network, source)
        cutout = refine_opaque_cutout(raw, edge_low=request.edge_low, edge_high=request.edge_high)
        qc = inspect_cutout(source, cutout)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp.png")
    cutout.save(temporary)
    os.replace(temporary, output)
    report = {
        "job_id": job_id,
        "status": "manual_review_required" if qc["passed"] else "qc_failed",
        "output": str(output.resolve()),
        "output_sha256": sha256_file(output),
        "model_id": model.id,
        "seconds_including_load": round(time.perf_counter() - started, 3),
        "peak_allocated_gib": round(torch.cuda.max_memory_allocated() / 2**30, 3),
        "input_check": input_check,
        "cutout_qc": qc,
        "visual_review_required": [
            "subject_geometry", "edge_halo", "original_shadow", "floor_reflection", *STOCK_REVIEW_CHECKS,
        ],
    }
    write_json(qc_file, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Remove background from an opaque isolated object")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--subject", choices=("opaque", "glass", "translucent"), required=True)
    parser.add_argument("--model-id", default="birefnet-dis")
    parser.add_argument("--jobs-dir", type=Path, default=ROOT / "jobs")
    parser.add_argument("--edge-low", type=int, default=5)
    parser.add_argument("--edge-high", type=int, default=250)
    args = parser.parse_args()
    try:
        request = BackgroundRequest(
            input=args.input, subject=args.subject, model_id=args.model_id,
            edge_low=args.edge_low, edge_high=args.edge_high,
        )
        report = run(request, args.jobs_dir)
    except Exception as exc:
        print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "manual_review_required" else 2


if __name__ == "__main__":
    raise SystemExit(main())
