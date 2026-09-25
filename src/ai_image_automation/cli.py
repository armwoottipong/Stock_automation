"""CLI for ComfyUI health, generation and upscale jobs."""

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from PIL import Image

from ai_image_automation.comfyui.client import ComfyUIClient, ComfyUIError
from ai_image_automation.config import ROOT, load_settings
from ai_image_automation.generation import GenerationRequest, build_sdxl_workflow, resolve_checkpoint
from ai_image_automation.jobs.runner import JobRunner
from ai_image_automation.quality.image_qc import check_generated_image
from ai_image_automation.quality.stock_policy import STOCK_REVIEW_CHECKS
from ai_image_automation.registry import LicenseRegistry, load_registry
from ai_image_automation.upscale import (
    CreativeUpscaleRequest, UpscaleRequest, build_creative_workflow, build_pixel_workflow,
    make_guided_image, resolve_controlnet, resolve_upscaler,
    run_creative_with_lowvram_retry, stage_input_image,
)


def main(argv: Sequence[str] | None = None) -> int:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Local ComfyUI API controller")
    parser.add_argument("--url", default=settings.comfyui.base_url, help="ComfyUI base URL")
    parser.add_argument("--jobs-dir", type=Path, default=ROOT / "jobs")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("health", help="Check ComfyUI API and GPU")
    submit = commands.add_parser("submit", help="Submit an API-format workflow JSON")
    submit.add_argument("--workflow", type=Path, required=True)
    resume = commands.add_parser("resume", help="Resume a queued job")
    resume.add_argument("job_id")
    generate = commands.add_parser("generate", help="Generate one image with a registered SDXL checkpoint")
    generate.add_argument("--prompt", required=True)
    generate.add_argument("--negative-prompt", default="")
    generate.add_argument("--model-id", default="sdxl-base-1.0")
    generate.add_argument("--registry", type=Path, default=ROOT / "data" / "model_registry.json")
    generate.add_argument("--license-registry", type=Path, default=ROOT / "data" / "license_registry.json")
    generate.add_argument("--checkpoints-dir", type=Path, default=ROOT / "vendor" / "ComfyUI" / "models" / "checkpoints")
    generate.add_argument("--noncommercial", action="store_true")
    generate.add_argument("--width", type=int, default=settings.generation.width)
    generate.add_argument("--height", type=int, default=settings.generation.height)
    generate.add_argument("--steps", type=int, default=settings.generation.steps)
    generate.add_argument("--cfg", type=float, default=settings.generation.cfg)
    generate.add_argument("--sampler-name", default=settings.generation.sampler_name)
    generate.add_argument("--scheduler", default=settings.generation.scheduler)
    generate.add_argument("--seed", type=int, default=0)
    upscale = commands.add_parser("upscale", help="Upscale an existing image 2× with a registered pixel model")
    upscale.add_argument("--input", type=Path, required=True)
    upscale.add_argument("--model-id", default="realesrgan-x2plus")
    upscale.add_argument("--registry", type=Path, default=ROOT / "data" / "upscaler_registry.json")
    upscale.add_argument("--license-registry", type=Path, default=ROOT / "data" / "license_registry.json")
    upscale.add_argument("--models-dir", type=Path, default=ROOT / "vendor" / "ComfyUI" / "models" / "upscale_models")
    upscale.add_argument("--comfy-input-dir", type=Path, default=ROOT / "vendor" / "ComfyUI" / "input")
    upscale.add_argument("--noncommercial", action="store_true")
    creative = commands.add_parser("creative-upscale", help="Refine an existing image with SDXL ControlNet tiles")
    creative.add_argument("--input", type=Path, required=True)
    creative.add_argument("--prompt", required=True)
    creative.add_argument("--negative-prompt", default="")
    creative.add_argument("--checkpoint-id", default="sdxl-base-1.0")
    creative.add_argument("--controlnet-id", default="xinsir-tile-sdxl-1.0")
    creative.add_argument("--checkpoint-registry", type=Path, default=ROOT / "data" / "model_registry.json")
    creative.add_argument("--controlnet-registry", type=Path, default=ROOT / "data" / "controlnet_registry.json")
    creative.add_argument("--license-registry", type=Path, default=ROOT / "data" / "license_registry.json")
    creative.add_argument("--checkpoints-dir", type=Path, default=ROOT / "vendor" / "ComfyUI" / "models" / "checkpoints")
    creative.add_argument("--controlnets-dir", type=Path, default=ROOT / "vendor" / "ComfyUI" / "models" / "controlnet")
    creative.add_argument("--comfy-input-dir", type=Path, default=ROOT / "vendor" / "ComfyUI" / "input")
    creative.add_argument("--tile", type=int, default=768)
    creative.add_argument("--padding", type=int, default=64)
    creative.add_argument("--denoise", type=float, default=0.34)
    creative.add_argument("--control-weight", type=float, default=0.88)
    creative.add_argument("--control-end", type=float, default=0.75)
    creative.add_argument("--seam-denoise", type=float, default=0.14)
    creative.add_argument("--seam-mask-blur", type=int, default=16)
    creative.add_argument("--steps", type=int, default=26)
    creative.add_argument("--cfg", type=float, default=5.0)
    creative.add_argument("--seed", type=int, default=0)
    creative.add_argument("--noncommercial", action="store_true")
    args = parser.parse_args(argv)

    client = ComfyUIClient(args.url, timeout_seconds=settings.comfyui.timeout_seconds)
    try:
        if args.command == "health":
            result = client.health()
        elif args.command == "creative-upscale":
            request = CreativeUpscaleRequest(
                input=args.input, prompt=args.prompt, negative_prompt=args.negative_prompt,
                tile=args.tile, padding=args.padding, denoise=args.denoise,
                control_weight=args.control_weight, control_end=args.control_end,
                seam_denoise=args.seam_denoise, seam_mask_blur=args.seam_mask_blur,
                steps=args.steps, cfg=args.cfg, seed=args.seed,
            )
            licenses = LicenseRegistry.model_validate_json(args.license_registry.read_text(encoding="utf-8"))
            checkpoint = resolve_checkpoint(
                load_registry(args.checkpoint_registry), args.checkpoint_id,
                commercial=not args.noncommercial, licenses=licenses,
            )
            controlnet = resolve_controlnet(
                load_registry(args.controlnet_registry), args.controlnet_id,
                commercial=not args.noncommercial, licenses=licenses,
            )
            for model, model_dir in ((checkpoint, args.checkpoints_dir), (controlnet, args.controlnets_dir)):
                model_path = Path(model.local_path or "")
                if not model_path.is_absolute():
                    model_path = ROOT / model_path
                if not model_path.resolve().is_relative_to(model_dir.resolve()):
                    raise ValueError(f"Model {model.id} is outside its ComfyUI model directory")
            staged = stage_input_image(request.input, args.comfy_input_dir)
            guided = make_guided_image(staged, staged.with_name("guided_" + staged.stem + ".png"))
            with Image.open(staged) as image:
                width, height = image.size
            def build_workflow(effective: CreativeUpscaleRequest) -> dict:
                return build_creative_workflow(
                    effective, image_name=staged.name, guide_name=guided.name,
                    checkpoint_name=Path(checkpoint.local_path or "").name,
                    controlnet_name=Path(controlnet.local_path or "").name,
                )

            record, effective = run_creative_with_lowvram_retry(
                request, build_workflow, JobRunner(client, args.jobs_dir).run,
            )
            job_dir = args.jobs_dir / record.job_id
            (job_dir / "request.json").write_text(json.dumps({
                **effective.model_dump(mode="json"), "task": "creative_upscale",
                "requested_tile": request.tile, "requested_padding": request.padding,
                "checkpoint_id": checkpoint.id, "controlnet_id": controlnet.id,
                "commercial": not args.noncommercial,
            }, indent=2), encoding="utf-8")
            (job_dir / "prompt.txt").write_text(request.prompt + "\n", encoding="utf-8")
            qc = [
                {"path": output, **check_generated_image(Path(output), width=width, height=height).__dict__,
                 "stock_review_required": list(STOCK_REVIEW_CHECKS)}
                for output in record.outputs
            ]
            (job_dir / "qc.json").write_text(json.dumps(qc, indent=2), encoding="utf-8")
            if not all(item["passed"] for item in qc):
                raise ValueError(f"Image QC failed: {qc}")
            result = record.__dict__
        elif args.command == "upscale":
            request = UpscaleRequest(input=args.input)
            licenses = LicenseRegistry.model_validate_json(args.license_registry.read_text(encoding="utf-8"))
            model = resolve_upscaler(
                load_registry(args.registry), args.model_id,
                commercial=not args.noncommercial, licenses=licenses,
            )
            model_path = Path(model.local_path or "")
            if not model_path.is_absolute():
                model_path = ROOT / model_path
            if not model_path.resolve().is_relative_to(args.models_dir.resolve()):
                raise ValueError("Upscaler must be inside the ComfyUI upscale models directory")
            staged = stage_input_image(request.input, args.comfy_input_dir)
            with Image.open(staged) as image:
                width, height = image.size
            workflow = build_pixel_workflow(request, staged.name, model)
            record = JobRunner(client, args.jobs_dir).run(workflow)
            job_dir = args.jobs_dir / record.job_id
            (job_dir / "request.json").write_text(json.dumps({
                "task": "upscale", "input": str(request.input.resolve()), "scale": request.scale,
                "model_id": model.id, "commercial": not args.noncommercial,
            }, indent=2), encoding="utf-8")
            qc = [
                {"path": output, **check_generated_image(Path(output), width=width * request.scale, height=height * request.scale).__dict__,
                 "stock_review_required": list(STOCK_REVIEW_CHECKS)}
                for output in record.outputs
            ]
            (job_dir / "qc.json").write_text(json.dumps(qc, indent=2), encoding="utf-8")
            if not all(item["passed"] for item in qc):
                raise ValueError(f"Image QC failed: {qc}")
            result = record.__dict__
        elif args.command == "generate":
            request = GenerationRequest(
                prompt=args.prompt, negative_prompt=args.negative_prompt,
                width=args.width, height=args.height, steps=args.steps,
                cfg=args.cfg, seed=args.seed, sampler_name=args.sampler_name,
                scheduler=args.scheduler,
            )
            licenses = LicenseRegistry.model_validate_json(args.license_registry.read_text(encoding="utf-8"))
            model = resolve_checkpoint(
                load_registry(args.registry), args.model_id,
                commercial=not args.noncommercial, licenses=licenses,
            )
            model_path = Path(model.local_path or "")
            if not model_path.is_absolute():
                model_path = ROOT / model_path
            if not model_path.resolve().is_relative_to(args.checkpoints_dir.resolve()):
                raise ValueError("Checkpoint must be inside the ComfyUI checkpoints directory")
            workflow = build_sdxl_workflow(request, model)
            record = JobRunner(client, args.jobs_dir).run(workflow)
            job_dir = args.jobs_dir / record.job_id
            (job_dir / "request.json").write_text(
                json.dumps({**request.model_dump(), "model_id": model.id, "commercial": not args.noncommercial}, indent=2),
                encoding="utf-8",
            )
            (job_dir / "prompt.txt").write_text(request.prompt + "\n", encoding="utf-8")
            qc = [
                {"path": output, **check_generated_image(Path(output), width=request.width, height=request.height).__dict__,
                 "stock_review_required": list(STOCK_REVIEW_CHECKS)}
                for output in record.outputs
            ]
            (job_dir / "qc.json").write_text(json.dumps(qc, indent=2), encoding="utf-8")
            if not all(item["passed"] for item in qc):
                raise ValueError(f"Image QC failed: {qc}")
            result = record.__dict__
        else:
            runner = JobRunner(client, args.jobs_dir)
            if args.command == "submit":
                workflow = json.loads(args.workflow.read_text(encoding="utf-8"))
                if not isinstance(workflow, dict):
                    raise ValueError("Workflow must be a JSON object")
                result = runner.run(workflow).__dict__
            else:
                result = runner.resume(args.job_id).__dict__
    except (ComfyUIError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
