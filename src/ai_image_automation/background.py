"""Deterministic validation and quality checks for opaque-object cutouts."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image, ImageOps
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai_image_automation.registry import LicenseRegistry, ModelRecord, Registry


class BackgroundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    input: Path
    subject: Literal["opaque", "glass", "translucent"]
    model_id: str = "birefnet-dis"
    edge_low: int = Field(default=5, ge=0, le=64)
    edge_high: int = Field(default=250, ge=191, le=255)

    @model_validator(mode="after")
    def valid_edge_thresholds(self) -> "BackgroundRequest":
        if self.edge_low >= self.edge_high:
            raise ValueError("edge_low must be below edge_high")
        return self


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_background_model(
    registry: Registry, licenses: LicenseRegistry, model_id: str, *, root: Path,
) -> tuple[ModelRecord, Path]:
    matches = [record for record in registry.eligible("remove_background", commercial=True) if record.id == model_id]
    if len(matches) != 1:
        raise ValueError(f"Background model {model_id} is not commercially eligible")
    model = matches[0]
    evidence = [record for record in licenses.records if record.resource_id == model_id]
    if len(evidence) != 1 or evidence[0].commercial_use != "allowed" or evidence[0].license != model.license:
        raise ValueError(f"Background model {model_id} lacks matching license evidence")
    if not model.installed or not model.local_path or not model.sha256:
        raise ValueError(f"Background model {model_id} has no verified local checkpoint")
    path = Path(model.local_path)
    path = path if path.is_absolute() else root / path
    path = path.resolve()
    if not path.is_relative_to((root / "vendor" / "background_models").resolve()):
        raise ValueError("Background checkpoint is outside the model cache")
    if not path.is_file() or sha256_file(path) != model.sha256:
        raise ValueError("Background checkpoint is missing or its SHA-256 differs from the registry")
    return model, path


def inspect_input(image: Image.Image) -> dict:
    rgb = np.asarray(ImageOps.exif_transpose(image).convert("RGB"), dtype=np.uint8)
    height, width = rgb.shape[:2]
    size = max(8, min(height, width) // 16)
    patches = [rgb[:size, :size], rgb[:size, -size:], rgb[-size:, :size], rgb[-size:, -size:]]
    centers = np.asarray([np.median(patch.reshape(-1, 3), axis=0) for patch in patches])
    within = np.asarray([np.percentile(np.abs(patch.astype(np.float32) - center), 90) for patch, center in zip(patches, centers)])
    spread = float(np.max(centers.max(axis=0) - centers.min(axis=0)))
    near_white = bool(np.min(centers) >= 245 and np.max(within) <= 8)
    simple_solid = bool(spread <= 24 and np.max(within) <= 12)
    return {
        "corner_median_rgb": centers.astype(int).tolist(),
        "corner_spread": round(spread, 1),
        "near_white": near_white,
        "simple_solid": simple_solid,
        "background_review_required": not (near_white or simple_solid),
    }


def refine_opaque_cutout(image: Image.Image, *, edge_low: int, edge_high: int) -> Image.Image:
    if edge_low >= edge_high:
        raise ValueError("edge_low must be below edge_high")
    rgba = np.asarray(image.convert("RGBA")).copy()
    alpha = rgba[:, :, 3]
    alpha[alpha <= edge_low] = 0
    alpha[alpha >= edge_high] = 255
    return Image.fromarray(rgba, "RGBA")


def inspect_cutout(source: Image.Image, cutout: Image.Image) -> dict:
    source_rgb = np.asarray(ImageOps.exif_transpose(source).convert("RGB"))
    rgba = np.asarray(cutout.convert("RGBA"))
    alpha = rgba[:, :, 3]
    issues: list[str] = []
    if rgba.shape[:2] != source_rgb.shape[:2]:
        issues.append("dimensions_changed")
        return {"passed": False, "issues": issues}
    if not np.array_equal(rgba[:, :, :3], source_rgb):
        issues.append("source_rgb_changed")
    foreground = alpha >= 128
    fraction = float(np.mean(foreground))
    if not np.any(foreground):
        issues.append("empty_foreground")
        bounds = None
    else:
        ys, xs = np.nonzero(foreground)
        bounds = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
        if xs.min() == 0 or ys.min() == 0 or xs.max() == alpha.shape[1] - 1 or ys.max() == alpha.shape[0] - 1:
            issues.append("foreground_touches_edge")
    if fraction > 0.9:
        issues.append("background_not_removed")
    if fraction < 0.005:
        issues.append("foreground_too_small")
    if int(alpha.min()) != 0 or int(alpha.max()) != 255:
        issues.append("incomplete_alpha_range")
    return {
        "passed": not issues,
        "issues": issues,
        "foreground_fraction": round(fraction, 6),
        "foreground_bounds_128": bounds,
        "partial_alpha_fraction": round(float(np.mean((alpha > 0) & (alpha < 255))), 6),
        "alpha_min": int(alpha.min()),
        "alpha_max": int(alpha.max()),
    }
