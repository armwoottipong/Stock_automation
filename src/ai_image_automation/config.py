"""Validated project settings. No model or node is installed by loading settings."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


ROOT = Path(__file__).resolve().parents[2]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HardwareSettings(StrictModel):
    target_vram_gb: float = Field(default=8, gt=0)
    available_vram_gb: float = Field(default=8, gt=0)
    lowvram: bool = True

    @model_validator(mode="after")
    def fits_hardware(self) -> "HardwareSettings":
        if self.target_vram_gb > self.available_vram_gb:
            raise ValueError("target_vram_gb exceeds available_vram_gb")
        return self


class ComfyUISettings(StrictModel):
    base_url: str = "http://127.0.0.1:8188"
    timeout_seconds: int = Field(default=30, gt=0)


class GenerationSettings(StrictModel):
    width: int = Field(default=1024, gt=0)
    height: int = Field(default=1024, gt=0)
    steps: int = Field(default=26, ge=1, le=100)
    cfg: float = Field(default=5.0, gt=0)
    sampler: str = "DPM++ 2M Karras"


class Settings(StrictModel):
    hardware: HardwareSettings = Field(default_factory=HardwareSettings)
    comfyui: ComfyUISettings = Field(default_factory=ComfyUISettings)
    generation: GenerationSettings = Field(default_factory=GenerationSettings)


def load_settings(path: Path | None = None) -> Settings:
    """Load a YAML settings file and reject invalid configuration."""
    source = path or ROOT / "config" / "default.yaml"
    with source.open(encoding="utf-8") as stream:
        raw: Any = yaml.safe_load(stream)
    if not isinstance(raw, dict):
        raise ValueError(f"Config must be a mapping: {source}")
    return Settings.model_validate(raw)
