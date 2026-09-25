"""Pixel upscaling workflow planning and safe ComfyUI input staging."""

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Callable, Literal, TypeVar

import numpy as np
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, ConfigDict, Field, model_validator
from scipy.ndimage import uniform_filter

from ai_image_automation.config import ROOT
from ai_image_automation.comfyui.client import ComfyUIError
from ai_image_automation.registry import LicenseRegistry, ModelRecord, Registry


T = TypeVar("T")


class UpscaleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: Path
    scale: Literal[2] = 2


class CreativeUpscaleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: Path
    prompt: str = Field(min_length=1)
    negative_prompt: str = ""
    seed: int = Field(default=0, ge=0, le=18446744073709551615)
    steps: int = Field(default=26, ge=1, le=100)
    cfg: float = Field(default=5.0, gt=0, le=20)
    sampler_name: str = "dpmpp_2m"
    scheduler: str = "karras"
    tile: int = Field(default=768, ge=256, le=1024)
    padding: int = Field(default=64, ge=0, le=256)
    denoise: float = Field(default=0.34, ge=0, le=1)
    control_weight: float = Field(default=0.88, ge=0, le=2)
    control_end: float = Field(default=0.75, ge=0, le=1)
    seam_denoise: float = Field(default=0.14, ge=0, le=1)
    seam_mask_blur: int = Field(default=16, ge=0, le=64)

    @model_validator(mode="after")
    def valid_tile(self) -> "CreativeUpscaleRequest":
        if self.tile % 8 or self.padding % 8:
            raise ValueError("tile and padding must be divisible by 8")
        return self


def stage_input_image(source: Path, input_dir: Path) -> Path:
    if source.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise ValueError("Input must be PNG, JPEG or WebP")
    try:
        with Image.open(source) as image:
            image.verify()
    except (OSError, UnidentifiedImageError) as exc:
        raise ValueError(f"Input is not a valid image: {source}") from exc
    digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
    input_dir.mkdir(parents=True, exist_ok=True)
    target = input_dir / f"upscale_{digest}{source.suffix.lower()}"
    if not target.exists():
        shutil.copy2(source, target)
    return target


def make_guided_image(source: Path, target: Path, *, radius: int = 8, eps: float = 0.01) -> Path:
    """Apply a grayscale-guided, color-preserving filter to a ControlNet hint."""
    if radius < 1 or eps <= 0:
        raise ValueError("Guided filter radius and eps must be positive")
    with Image.open(source) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    guide = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    size = 2 * radius + 1
    mean_guide = uniform_filter(guide, size=size, mode="reflect")
    variance = uniform_filter(guide * guide, size=size, mode="reflect") - mean_guide * mean_guide
    result = np.empty_like(rgb)
    for channel in range(3):
        plane = rgb[:, :, channel]
        mean_plane = uniform_filter(plane, size=size, mode="reflect")
        covariance = uniform_filter(guide * plane, size=size, mode="reflect") - mean_guide * mean_plane
        a = covariance / (variance + eps)
        b = mean_plane - a * mean_guide
        result[:, :, channel] = uniform_filter(a, size=size, mode="reflect") * guide + uniform_filter(b, size=size, mode="reflect")
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.uint8(np.clip(result * 255.0, 0, 255))).save(target)
    return target


def resolve_upscaler(
    registry: Registry, model_id: str, *, commercial: bool,
    licenses: LicenseRegistry | None = None,
) -> ModelRecord:
    model = next((record for record in registry.records if record.id == model_id), None)
    if model is None or "upscale" not in model.tasks:
        raise ValueError(f"Unknown upscaler: {model_id}")
    if commercial and model not in registry.eligible("upscale", commercial=True):
        raise ValueError(f"Upscaler {model_id} is not cleared for commercial use")
    if commercial:
        license_record = next((record for record in (licenses.records if licenses else []) if record.resource_id == model_id), None)
        if (
            license_record is None or license_record.commercial_use != "allowed"
            or license_record.license != model.license or not license_record.source
            or not license_record.last_verified
        ):
            raise ValueError(f"Upscaler {model_id} has no matching commercial license registry record")
    if not model.installed or not model.local_path:
        raise ValueError(f"Upscaler {model_id} is not installed")
    path = Path(model.local_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        raise FileNotFoundError(path)
    return model


def resolve_controlnet(
    registry: Registry, model_id: str, *, commercial: bool,
    licenses: LicenseRegistry | None = None,
) -> ModelRecord:
    model = next((record for record in registry.records if record.id == model_id), None)
    if model is None or "creative_upscale" not in model.tasks:
        raise ValueError(f"Unknown creative upscale ControlNet: {model_id}")
    if commercial and model not in registry.eligible("creative_upscale", commercial=True):
        raise ValueError(f"ControlNet {model_id} is not cleared for commercial use")
    if commercial:
        license_record = next((record for record in (licenses.records if licenses else []) if record.resource_id == model_id), None)
        if (
            license_record is None or license_record.commercial_use != "allowed"
            or license_record.license != model.license or not license_record.source
            or not license_record.last_verified
        ):
            raise ValueError(f"ControlNet {model_id} has no matching commercial license registry record")
    if not model.installed or not model.local_path:
        raise ValueError(f"ControlNet {model_id} is not installed")
    path = Path(model.local_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        raise FileNotFoundError(path)
    return model


def build_pixel_workflow(request: UpscaleRequest, image_name: str, model: ModelRecord) -> dict[str, Any]:
    if Path(image_name).name != image_name:
        raise ValueError("ComfyUI image name must be a basename")
    template = ROOT / "workflows" / "templates" / "upscale_pixel.json"
    workflow: dict[str, Any] = json.loads(template.read_text(encoding="utf-8"))
    workflow["1"]["inputs"]["image"] = image_name
    workflow["2"]["inputs"]["model_name"] = Path(model.local_path or "").name
    return workflow


def build_creative_workflow(
    request: CreativeUpscaleRequest, *, image_name: str, guide_name: str,
    checkpoint_name: str, controlnet_name: str,
) -> dict[str, Any]:
    for name in (image_name, guide_name, checkpoint_name, controlnet_name):
        if Path(name).name != name:
            raise ValueError("ComfyUI model and image names must be basenames")
    template = ROOT / "workflows" / "templates" / "upscale_creative_sdxl.json"
    workflow: dict[str, Any] = json.loads(template.read_text(encoding="utf-8"))
    workflow["1"]["inputs"]["image"] = image_name
    workflow["2"]["inputs"]["image"] = guide_name
    workflow["3"]["inputs"]["ckpt_name"] = checkpoint_name
    workflow["4"]["inputs"]["text"] = request.prompt
    workflow["5"]["inputs"]["text"] = request.negative_prompt
    workflow["6"]["inputs"]["control_net_name"] = controlnet_name
    workflow["7"]["inputs"].update(strength=request.control_weight, end_percent=request.control_end)
    workflow["8"]["inputs"].update(
        seed=request.seed, steps=request.steps, cfg=request.cfg,
        sampler_name=request.sampler_name, scheduler=request.scheduler,
        denoise=request.denoise, tile_width=request.tile, tile_height=request.tile,
        tile_padding=request.padding, seam_fix_denoise=request.seam_denoise,
        seam_fix_mask_blur=request.seam_mask_blur,
    )
    return workflow


def run_creative_with_lowvram_retry(
    request: CreativeUpscaleRequest,
    build: Callable[[CreativeUpscaleRequest], dict[str, Any]],
    run: Callable[[dict[str, Any]], T],
) -> tuple[T, CreativeUpscaleRequest]:
    try:
        return run(build(request)), request
    except ComfyUIError as exc:
        if "out of memory" not in str(exc).lower() or request.tile <= 512:
            raise
    retry = request.model_copy(update={"tile": 512, "padding": min(request.padding, 32)})
    return run(build(retry)), retry
