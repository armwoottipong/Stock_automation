"""Run a frozen same-case generation comparison; never select a production model."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_image_automation.background import sha256_file  # noqa: E402
from ai_image_automation.comfyui.client import ComfyUIClient  # noqa: E402
from ai_image_automation.generation import GenerationRequest, build_sdxl_workflow, resolve_checkpoint  # noqa: E402
from ai_image_automation.jobs.runner import JobRunner  # noqa: E402
from ai_image_automation.quality.image_qc import check_generated_image  # noqa: E402
from ai_image_automation.registry import LicenseRegistry, load_registry  # noqa: E402


DEFAULT_RUN = ROOT / "benchmarks" / "generation" / "2026-09-26" / "run.json"
FLUX_COMPONENTS = ("flux2-klein-4b-fp8", "flux2-klein-qwen3-4b-fp4", "flux2-klein-vae")


def checked_model(model_id: str):
    registry = load_registry(ROOT / "data" / "model_registry.json")
    licenses = LicenseRegistry.model_validate_json((ROOT / "data" / "license_registry.json").read_text(encoding="utf-8"))
    model = resolve_checkpoint(registry, model_id, commercial=True, licenses=licenses)
    path = ROOT / (model.local_path or "")
    if not model.sha256 or sha256_file(path) != model.sha256:
        raise ValueError(f"Checkpoint hash mismatch for {model_id}")
    return model


def build_workflow(model_id: str, case: dict, size: tuple[int, int], parameters: dict) -> dict:
    if model_id == "sdxl-base-1.0":
        model = checked_model(model_id)
        request = GenerationRequest(
            prompt=case["prompt"], negative_prompt="gradient background, gray backdrop, props, text, logos, branding",
            width=size[0], height=size[1], steps=parameters["steps"], cfg=parameters["cfg"],
            seed=case["seed"], sampler_name=parameters["sampler"], scheduler=parameters["scheduler"],
        )
        workflow = build_sdxl_workflow(request, model)
        workflow["7"]["inputs"]["filename_prefix"] = f"generation_benchmark_sdxl_{case['id']}"
        return workflow
    if model_id != "flux2-klein-4b-fp8":
        raise ValueError(f"Unsupported benchmark model: {model_id}")
    components = {component: checked_model(component) for component in FLUX_COMPONENTS}
    workflow = json.loads((ROOT / parameters["workflow"]).read_text(encoding="utf-8"))
    workflow["1"]["inputs"]["unet_name"] = Path(components[FLUX_COMPONENTS[0]].local_path or "").name
    workflow["2"]["inputs"]["clip_name"] = Path(components[FLUX_COMPONENTS[1]].local_path or "").name
    workflow["3"]["inputs"]["vae_name"] = Path(components[FLUX_COMPONENTS[2]].local_path or "").name
    workflow["4"]["inputs"]["text"] = case["prompt"]
    workflow["6"]["inputs"]["cfg"] = parameters["cfg"]
    workflow["7"]["inputs"].update(width=size[0], height=size[1])
    workflow["8"]["inputs"].update(steps=parameters["steps"], width=size[0], height=size[1])
    workflow["9"]["inputs"]["noise_seed"] = case["seed"]
    workflow["10"]["inputs"]["sampler_name"] = parameters["sampler"]
    workflow["13"]["inputs"]["filename_prefix"] = f"generation_benchmark_flux2_{case['id']}"
    return workflow


def sample_gpu(stop: threading.Event, samples: list[int]) -> None:
    while not stop.is_set():
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=3, check=True,
            )
            samples.append(int(result.stdout.splitlines()[0].strip()))
        except (OSError, ValueError, IndexError, subprocess.SubprocessError):
            pass
        stop.wait(0.5)


def corner_rgb_mean(path: Path) -> list[float]:
    with Image.open(path) as image:
        rgb = image.convert("RGB")
        points = ((0, 0), (rgb.width - 1, 0), (0, rgb.height - 1), (rgb.width - 1, rgb.height - 1))
        values = [rgb.getpixel(point) for point in points]
    return [round(sum(pixel[channel] for pixel in values) / len(values), 1) for channel in range(3)]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--model", choices=("sdxl-base-1.0", "flux2-klein-4b-fp8"), required=True)
    parser.add_argument("--case", action="append", help="Run only this case ID; repeat for multiple cases")
    args = parser.parse_args()
    run_file = args.run.resolve()
    run = json.loads(run_file.read_text(encoding="utf-8"))
    cases = json.loads((run_file.parent / run["cases"]).read_text(encoding="utf-8"))
    if run["schema_version"] != 1 or cases["schema_version"] != 1:
        raise ValueError("Unsupported generation benchmark manifest")
    selected = [case for case in cases["cases"] if not args.case or case["id"] in args.case]
    if not selected or (args.case and set(args.case) != {case["id"] for case in selected}):
        raise ValueError("Unknown or empty benchmark case selection")
    size = (cases["width"], cases["height"])
    parameters = run["models"][args.model]
    output_dir = run_file.parent / "output" / args.model
    output_dir.mkdir(parents=True, exist_ok=True)
    client = ComfyUIClient("http://127.0.0.1:8188")
    client.health()
    runner = JobRunner(client, ROOT / "jobs")
    for case in selected:
        destination = output_dir / f"{case['id']}.png"
        result_file = output_dir / f"{case['id']}.json"
        if destination.exists() or result_file.exists():
            if destination.is_file() and result_file.is_file():
                print(f"Existing result preserved: {case['id']}", flush=True)
                continue
            raise ValueError(f"Incomplete result exists for {case['id']}; inspect it before retry")
        workflow = build_workflow(args.model, case, size, parameters)
        stop = threading.Event()
        samples: list[int] = []
        monitor = threading.Thread(target=sample_gpu, args=(stop, samples), daemon=True)
        monitor.start()
        started = time.perf_counter()
        try:
            record = runner.run(workflow)
            if len(record.outputs) != 1:
                raise ValueError(f"Expected one output for {case['id']}")
            source = Path(record.outputs[0])
            qc = check_generated_image(source, width=size[0], height=size[1])
            if not qc.passed:
                raise ValueError(f"Structural QC failed for {case['id']}: {qc.issues}")
            shutil.copy2(source, destination)
            result = {
                "status": "completed_requires_visual_review",
                "model_id": args.model, "case_id": case["id"], "job_id": record.job_id,
                "source_sha256": sha256_file(source), "output_sha256": sha256_file(destination),
                "seconds_including_load": round(time.perf_counter() - started, 2),
                "dimensions": list(size), "corner_rgb_mean": corner_rgb_mean(destination),
                "review_focus": case["review_focus"],
            }
            print(json.dumps(result), flush=True)
        except Exception as exc:
            result = {"status": "failed", "model_id": args.model, "case_id": case["id"],
                      "error_type": type(exc).__name__, "error": str(exc)}
            print(json.dumps(result), flush=True)
        finally:
            stop.set()
            monitor.join(timeout=4)
        result["peak_board_used_mib"] = max(samples) if samples else None
        result_file.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        if result["status"] == "failed":
            raise RuntimeError(f"Benchmark failed for {case['id']}; inspect {result_file}")


if __name__ == "__main__":
    main()
