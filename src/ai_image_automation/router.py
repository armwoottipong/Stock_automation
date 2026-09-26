"""Freeze an offline image-job decision before deterministic execution."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Annotated, Literal, Union

from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

from ai_image_automation.background import sha256_file
from ai_image_automation.generation import GenerationRequest
from ai_image_automation.quality.stock_policy import STOCK_REVIEW_CHECKS, with_stock_negative_prompt
from ai_image_automation.research_cache import ResearchContext, load_context, lookup
from ai_image_automation.upscale import CreativeUpscaleRequest


class StrictIntent(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GenerateIntent(StrictIntent):
    operation: Literal["generate"]
    subject_type: Literal["isolated_object"] = "isolated_object"
    description: str = Field(min_length=3, max_length=240)
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    steps: int = 26
    cfg: float = 5.0
    seed: int = 0
    sampler_name: str = "dpmpp_2m"
    scheduler: str = "karras"


class PixelUpscaleIntent(StrictIntent):
    operation: Literal["upscale"]
    subject_type: Literal["pixel_2x", "pixel_4x"] | None = None
    scale: Literal[2, 4] = 4
    input: Path

    @model_validator(mode="after")
    def match_scale(self) -> "PixelUpscaleIntent":
        if self.subject_type is None:
            self.subject_type = f"pixel_{self.scale}x"
        if self.subject_type != f"pixel_{self.scale}x":
            raise ValueError("subject_type and scale must match")
        return self


class CreativeUpscaleIntent(StrictIntent):
    operation: Literal["creative_upscale"]
    subject_type: Literal["product_refine"] = "product_refine"
    input: Path
    prompt: str = Field(min_length=3, max_length=500)
    negative_prompt: str = ""
    seed: int = 0
    steps: int = 26
    cfg: float = 5.0
    sampler_name: str = "dpmpp_2m"
    scheduler: str = "karras"
    tile: int = 768
    padding: int = 64
    denoise: float = 0.34
    control_weight: float = 0.88
    control_end: float = 0.75
    seam_denoise: float = 0.14
    seam_mask_blur: int = 16


class RemoveBackgroundIntent(StrictIntent):
    operation: Literal["remove_background"]
    subject_type: Literal["opaque_isolate", "glass_isolate", "translucent_isolate"]
    input: Path


Intent = Annotated[
    Union[GenerateIntent, PixelUpscaleIntent, CreativeUpscaleIntent, RemoveBackgroundIntent],
    Field(discriminator="operation"),
]
INTENT_ADAPTER = TypeAdapter(Intent)
FORBIDDEN_CONTENT = re.compile(r"\b(?:text|letters?|numbers?|logos?|trademarks?|watermarks?|labels?|branding|brands?)\b", re.I)


def parse_intent(value: dict) -> Intent:
    return INTENT_ADAPTER.validate_python(value)


def _prompt_description(description: str) -> str:
    clean = " ".join(description.split()).strip(" .,;")
    if not clean or FORBIDDEN_CONTENT.search(clean):
        raise ValueError("Object description requests text or branding, or is empty")
    return (
        f"One plain unbranded {clean}, entire object visible with generous margins, "
        "centered product photograph, pure white seamless background, even diffuse studio lighting, "
        "no props, isolated object"
    )


def _research(context: ResearchContext, task: str, subject: str, *, as_of: date | None) -> tuple[dict, str | None, str]:
    result = lookup(context, task, subject, as_of=as_of)
    if result.status != "fresh" or result.entry is None:
        raise ValueError(f"No fresh reviewed research for {task}/{subject}: {result.status} ({result.reason})")
    entry_json = result.entry.model_dump(mode="json")
    entry_digest = hashlib.sha256(json.dumps(entry_json, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return {
        "task": task, "subject_type": subject, "verified_at": result.entry.verified_at.isoformat(),
        "expires_at": result.entry.expires_at.isoformat(), "outcome": result.entry.outcome,
        "selected_model_id": result.usable_model_id, "entry_sha256": entry_digest,
    }, result.usable_model_id, result.entry.outcome


def _model_snapshot(context: ResearchContext, model_id: str) -> dict:
    model = context.models[model_id]
    if not model.sha256 or not model.local_path:
        raise ValueError(f"Model {model_id} lacks a registered checkpoint hash")
    return {
        "id": model.id, "version": model.version, "sha256": model.sha256,
        "local_path": model.local_path, "license": model.license,
        "last_verified": model.last_verified.isoformat() if model.last_verified else None,
    }


def _input_snapshot(path: Path) -> dict:
    source = path.resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    with Image.open(source) as image:
        image.verify()
    with Image.open(source) as image:
        size = list(image.size)
    return {"path": str(source), "sha256": sha256_file(source), "size": size}


def build_plan(intent: Intent, context: ResearchContext, *, as_of: date | None = None) -> dict:
    research: list[dict] = []
    models: dict[str, dict] = {}
    input_info: dict | None = None
    route: Literal["execute", "manual_review"] = "execute"
    retry_policy: dict | None = None

    if isinstance(intent, GenerateIntent):
        evidence, model_id, _ = _research(context, "generate", intent.subject_type, as_of=as_of)
        research.append(evidence)
        if not model_id:
            raise ValueError("No generation model selected")
        models["checkpoint"] = _model_snapshot(context, model_id)
        extra_negative = ", ".join(filter(None, (
            intent.negative_prompt.strip(), "busy background, gradient backdrop, person, hands, props",
        )))
        request = GenerationRequest(
            prompt=_prompt_description(intent.description),
            negative_prompt=with_stock_negative_prompt(extra_negative),
            width=intent.width, height=intent.height, steps=intent.steps, cfg=intent.cfg,
            seed=intent.seed, sampler_name=intent.sampler_name, scheduler=intent.scheduler,
        ).model_dump(mode="json")
        workflow = "generate_sdxl"
    elif isinstance(intent, PixelUpscaleIntent):
        evidence, model_id, _ = _research(context, "upscale", intent.subject_type, as_of=as_of)
        research.append(evidence)
        if not model_id:
            raise ValueError("No pixel upscaler selected")
        models["upscaler"] = _model_snapshot(context, model_id)
        input_info = _input_snapshot(intent.input)
        request = {"input": input_info["path"], "scale": intent.scale}
        workflow = "upscale_pixel"
    elif isinstance(intent, CreativeUpscaleIntent):
        checkpoint_evidence, checkpoint_id, _ = _research(context, "generate", "isolated_object", as_of=as_of)
        control_evidence, control_id, _ = _research(context, "creative_upscale", intent.subject_type, as_of=as_of)
        research.extend((checkpoint_evidence, control_evidence))
        if not checkpoint_id or not control_id:
            raise ValueError("Creative upscale requires checkpoint and ControlNet selections")
        models["checkpoint"] = _model_snapshot(context, checkpoint_id)
        models["controlnet"] = _model_snapshot(context, control_id)
        input_info = _input_snapshot(intent.input)
        if FORBIDDEN_CONTENT.search(intent.prompt):
            raise ValueError("Creative prompt requests text or branding")
        request = CreativeUpscaleRequest(
            **intent.model_dump(exclude={"operation", "subject_type", "negative_prompt"}),
            negative_prompt=with_stock_negative_prompt(intent.negative_prompt),
        ).model_dump(mode="json")
        request["input"] = input_info["path"]
        workflow = "upscale_creative_sdxl"
        if request["tile"] > 512:
            retry_policy = {
                "on_cuda_oom": "retry_once", "tile": 512,
                "padding": min(request["padding"], 32),
            }
    else:
        evidence, model_id, outcome = _research(context, "remove_background", intent.subject_type, as_of=as_of)
        research.append(evidence)
        input_info = _input_snapshot(intent.input)
        request = {"input": input_info["path"], "subject": intent.subject_type.split("_")[0]}
        workflow = "remove_background_birefnet" if outcome == "selected" else "manual_review"
        if outcome == "selected":
            if not model_id:
                raise ValueError("No background model selected")
            models["background"] = _model_snapshot(context, model_id)
        else:
            route = "manual_review"

    templates = {
        "generate_sdxl": "workflows/templates/generate_sdxl.json",
        "upscale_pixel": "workflows/templates/upscale_pixel.json",
        "upscale_creative_sdxl": "workflows/templates/upscale_creative_sdxl.json",
    }
    template_path = templates.get(workflow)
    template = (
        {"path": template_path, "sha256": sha256_file(context.root / template_path)}
        if template_path else None
    )
    payload = {
        "schema_version": 1,
        "operation": intent.operation,
        "subject_type": intent.subject_type,
        "route": route,
        "workflow": workflow,
        "workflow_template": template,
        "retry_policy": retry_policy,
        "request": request,
        "input": input_info,
        "models": models,
        "research": research,
        "stock_review_required": list(STOCK_REVIEW_CHECKS),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
    return {"plan_id": digest, **payload}


def freeze_plan(plan: dict, jobs_dir: Path) -> Path:
    destination = jobs_dir / plan["plan_id"] / "plan.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(plan, indent=2, ensure_ascii=False) + "\n"
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if json.loads(destination.read_text(encoding="utf-8")) != plan:
            raise ValueError("Existing frozen plan differs")
    else:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(serialized)
    return destination


def load_plan(path: Path) -> dict:
    plan = json.loads(path.read_text(encoding="utf-8"))
    payload = {key: value for key, value in plan.items() if key != "plan_id"}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
    if plan.get("plan_id") != digest:
        raise ValueError("Frozen plan hash mismatch")
    return plan


def _command(plan: dict, root: Path) -> list[str] | None:
    request = plan["request"]
    models = plan["models"]
    if plan["route"] == "manual_review":
        return None
    if plan["workflow"] == "generate_sdxl":
        return [sys.executable, str(root / "controller.py"), "generate", "--model-id", models["checkpoint"]["id"],
                "--prompt", request["prompt"], "--negative-prompt", request["negative_prompt"],
                "--width", str(request["width"]), "--height", str(request["height"]),
                "--steps", str(request["steps"]), "--cfg", str(request["cfg"]), "--seed", str(request["seed"]),
                "--sampler-name", request["sampler_name"], "--scheduler", request["scheduler"]]
    if plan["workflow"] == "upscale_pixel":
        return [sys.executable, str(root / "controller.py"), "upscale", "--model-id", models["upscaler"]["id"],
                "--input", request["input"], "--scale", str(request["scale"])]
    if plan["workflow"] == "upscale_creative_sdxl":
        return [sys.executable, str(root / "controller.py"), "creative-upscale",
                "--checkpoint-id", models["checkpoint"]["id"], "--controlnet-id", models["controlnet"]["id"],
                "--input", request["input"], "--prompt", request["prompt"],
                "--negative-prompt", request["negative_prompt"],
                "--sampler-name", request["sampler_name"], "--scheduler", request["scheduler"],
                *[item for name in (
                    "seed", "steps", "cfg", "tile", "padding", "denoise", "control_weight", "control_end",
                    "seam_denoise", "seam_mask_blur",
                ) for item in ("--" + name.replace("_", "-"), str(request[name]))]]
    if plan["workflow"] == "remove_background_birefnet":
        return [str(root / ".venv-comfyui" / "Scripts" / "python.exe"), str(root / "scripts" / "remove_background.py"),
                "--input", request["input"], "--subject", request["subject"], "--model-id", models["background"]["id"]]
    raise ValueError("Unknown frozen workflow")


def run_plan(path: Path, *, root: Path, as_of: date | None = None) -> dict:
    plan = load_plan(path)
    if plan.get("schema_version") != 1 or plan.get("route") not in ("execute", "manual_review"):
        raise ValueError("Unsupported frozen plan")
    context = load_context(root / "data")
    for evidence in plan["research"]:
        current = lookup(context, evidence["task"], evidence["subject_type"], as_of=as_of)
        if current.status != "fresh" or current.entry is None:
            raise ValueError("Research expired or changed; create a new plan")
        if (current.entry.verified_at.isoformat() != evidence["verified_at"]
                or current.entry.expires_at.isoformat() != evidence["expires_at"]
                or current.entry.outcome != evidence["outcome"]
                or current.usable_model_id != evidence["selected_model_id"]):
            raise ValueError("Research decision changed; create a new plan")
        current_json = current.entry.model_dump(mode="json")
        current_digest = hashlib.sha256(json.dumps(current_json, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        if current_digest != evidence["entry_sha256"]:
            raise ValueError("Research evidence changed; create a new plan")
    if plan["input"] and sha256_file(Path(plan["input"]["path"])) != plan["input"]["sha256"]:
        raise ValueError("Input image changed after planning")
    if plan.get("workflow_template"):
        template = plan["workflow_template"]
        if sha256_file(root / template["path"]) != template["sha256"]:
            raise ValueError("Workflow template changed after planning")
    for snapshot in plan["models"].values():
        current = context.models.get(snapshot["id"])
        if (current is None or current.sha256 != snapshot["sha256"] or current.local_path != snapshot["local_path"]
                or current.version != snapshot["version"] or current.license != snapshot["license"]
                or (current.last_verified.isoformat() if current.last_verified else None) != snapshot["last_verified"]):
            raise ValueError("Registered model changed after planning")
        checkpoint = Path(snapshot["local_path"])
        checkpoint = checkpoint if checkpoint.is_absolute() else root / checkpoint
        if sha256_file(checkpoint) != snapshot["sha256"]:
            raise ValueError("Model checkpoint hash mismatch")

    execution_file = path.parent / "execution.json"
    if execution_file.exists():
        recorded = json.loads(execution_file.read_text(encoding="utf-8"))
        outputs = recorded.get("outputs", [])
        if (recorded.get("plan_id") == plan["plan_id"]
                and ((plan["route"] == "manual_review" and recorded.get("status") == "manual_review_required"
                      and outputs == [])
                     or (plan["route"] == "execute" and recorded.get("status") == "completed_requires_review"
                         and isinstance(outputs, list) and bool(outputs)
                         and all(isinstance(output, str) and Path(output).is_file() for output in outputs)))):
            return recorded
    command = _command(plan, root)
    if command is None:
        record = {"plan_id": plan["plan_id"], "status": "manual_review_required", "outputs": []}
    else:
        completed = subprocess.run(command, cwd=root, capture_output=True, text=True)
        if completed.returncode:
            detail = completed.stderr.lower()
            if "out of memory" in detail:
                category = "CUDA out of memory"
            elif "timed out" in detail or "timeout" in detail:
                category = "timed out"
            elif "connection refused" in detail or "connection reset" in detail:
                category = "connection unavailable"
            else:
                category = "execution failure"
            raise RuntimeError(f"Frozen job failed with exit code {completed.returncode}: {category}")
        result = json.loads(completed.stdout)
        outputs = result.get("outputs") or ([result["output"]] if result.get("output") else [])
        if not outputs:
            raise RuntimeError("Frozen job returned no output images")
        if not all(isinstance(output, str) and Path(output).is_file() for output in outputs):
            raise RuntimeError("Frozen job returned missing output images")
        record = {
            "plan_id": plan["plan_id"], "status": "completed_requires_review", "outputs": outputs,
            "underlying_job_id": result.get("job_id"),
        }
    temporary = execution_file.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, execution_file)
    return record
