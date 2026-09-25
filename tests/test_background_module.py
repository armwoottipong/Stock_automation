from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from ai_image_automation.background import (
    inspect_cutout, inspect_input, refine_opaque_cutout, resolve_background_model,
)
from ai_image_automation.registry import LicenseRecord, LicenseRegistry, ModelRecord, Registry


def test_simple_background_check_distinguishes_white_solid_and_busy():
    white = Image.new("RGB", (128, 128), "white")
    assert inspect_input(white)["near_white"]
    gray = Image.new("RGB", (128, 128), (130, 130, 130))
    assert inspect_input(gray)["simple_solid"]
    assert not inspect_input(gray)["near_white"]
    busy = np.zeros((128, 128, 3), dtype=np.uint8)
    busy[:64] = 40
    busy[64:] = 210
    assert inspect_input(Image.fromarray(busy))["background_review_required"]


def test_refinement_preserves_rgb_and_reports_geometry():
    source = Image.new("RGB", (64, 64), (30, 80, 120))
    rgba = source.convert("RGBA")
    alpha = Image.new("L", (64, 64), 0)
    for y in range(10, 54):
        for x in range(10, 54):
            alpha.putpixel((x, y), 255)
    alpha.putpixel((8, 8), 3)
    rgba.putalpha(alpha)
    refined = refine_opaque_cutout(rgba, edge_low=5, edge_high=250)
    qc = inspect_cutout(source, refined)
    assert refined.getpixel((8, 8))[3] == 0
    assert qc["passed"]
    assert qc["foreground_bounds_128"] == [10, 10, 53, 53]
    changed = refined.copy()
    changed.putpixel((20, 20), (0, 0, 0, 255))
    assert "source_rgb_changed" in inspect_cutout(source, changed)["issues"]


def test_background_model_requires_license_and_exact_checkpoint(tmp_path: Path):
    model_dir = tmp_path / "vendor" / "background_models" / "birefnet-dis"
    model_dir.mkdir(parents=True)
    checkpoint = model_dir / "model.safetensors"
    checkpoint.write_bytes(b"checkpoint")
    import hashlib

    model = ModelRecord(
        id="birefnet-dis", name="BiRefNet", tasks=["remove_background"],
        commercial_use="allowed", license="MIT", source="https://example.org/publisher",
        last_verified="2026-09-25", installed=True,
        local_path=str(checkpoint), sha256=hashlib.sha256(b"checkpoint").hexdigest(),
    )
    licenses = LicenseRegistry(records=[LicenseRecord(
        resource_id=model.id, license="MIT", commercial_use="allowed",
        source="https://example.org/license", last_verified="2026-09-25",
    )])
    assert resolve_background_model(Registry(records=[model]), licenses, model.id, root=tmp_path)[1] == checkpoint
    with pytest.raises(ValueError, match="license evidence"):
        resolve_background_model(Registry(records=[model]), LicenseRegistry(), model.id, root=tmp_path)
    checkpoint.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="SHA-256"):
        resolve_background_model(Registry(records=[model]), licenses, model.id, root=tmp_path)
