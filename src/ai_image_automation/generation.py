"""SDXL generation planning and API workflow parameter injection."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai_image_automation.config import ROOT
from ai_image_automation.quality.stock_policy import with_stock_negative_prompt
from ai_image_automation.registry import LicenseRegistry, ModelRecord, Registry


class GenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1)
    negative_prompt: str = ""
    width: int = Field(default=1024, ge=64, le=2048)
    height: int = Field(default=1024, ge=64, le=2048)
    steps: int = Field(default=26, ge=1, le=100)
    cfg: float = Field(default=5.0, gt=0, le=20)
    seed: int = Field(default=0, ge=0, le=18446744073709551615)
    sampler_name: str = Field(default="dpmpp_2m", min_length=1)
    scheduler: str = Field(default="karras", min_length=1)

    @model_validator(mode="after")
    def valid_dimensions(self) -> "GenerationRequest":
        if self.width % 8 or self.height % 8:
            raise ValueError("width and height must be divisible by 8")
        return self


def resolve_checkpoint(
    registry: Registry, model_id: str, *, commercial: bool,
    licenses: LicenseRegistry | None = None,
) -> ModelRecord:
    model = next((record for record in registry.records if record.id == model_id), None)
    if model is None or "generate" not in model.tasks:
        raise ValueError(f"Unknown generation model: {model_id}")
    if commercial and model not in registry.eligible("generate", commercial=True):
        raise ValueError(f"Model {model_id} is not cleared for commercial use")
    if commercial:
        license_record = next((record for record in (licenses.records if licenses else []) if record.resource_id == model_id), None)
        if (
            license_record is None
            or license_record.commercial_use != "allowed"
            or license_record.license != model.license
            or not license_record.source
            or not license_record.last_verified
        ):
            raise ValueError(f"Model {model_id} has no matching commercial license registry record")
    if not model.installed or not model.local_path:
        raise ValueError(f"Model {model_id} is not installed")
    path = Path(model.local_path)
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        raise FileNotFoundError(path)
    return model


def build_sdxl_workflow(request: GenerationRequest, model: ModelRecord) -> dict[str, Any]:
    template = ROOT / "workflows" / "templates" / "generate_sdxl.json"
    workflow: dict[str, Any] = json.loads(template.read_text(encoding="utf-8"))
    workflow["1"]["inputs"]["ckpt_name"] = Path(model.local_path or "").name
    workflow["2"]["inputs"]["text"] = request.prompt
    workflow["3"]["inputs"]["text"] = with_stock_negative_prompt(request.negative_prompt)
    workflow["4"]["inputs"].update(width=request.width, height=request.height)
    workflow["5"]["inputs"].update(
        seed=request.seed, steps=request.steps, cfg=request.cfg,
        sampler_name=request.sampler_name, scheduler=request.scheduler,
    )
    return workflow
