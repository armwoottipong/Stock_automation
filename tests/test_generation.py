from pathlib import Path

import pytest
from PIL import Image

from ai_image_automation.generation import GenerationRequest, build_sdxl_workflow, resolve_checkpoint
from ai_image_automation.quality.image_qc import check_generated_image
from ai_image_automation.registry import LicenseRecord, LicenseRegistry, ModelRecord, Registry


def installed_model(tmp_path: Path) -> ModelRecord:
    checkpoint = tmp_path / "sdxl.safetensors"
    checkpoint.write_bytes(b"test")
    return ModelRecord(
        id="sdxl-base-1.0",
        name="SDXL Base 1.0",
        tasks=["generate"],
        commercial_use="allowed",
        license="CreativeML Open RAIL++-M",
        source="https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0",
        last_verified="2026-09-25",
        installed=True,
        local_path=str(checkpoint),
    )


def test_workflow_injects_prompt_and_generation_parameters(tmp_path):
    request = GenerationRequest(
        prompt="glass perfume bottle", negative_prompt="text, watermark",
        width=1024, height=1024, steps=26, cfg=5.0, seed=123,
        sampler_name="euler", scheduler="simple",
    )
    model = installed_model(tmp_path)
    workflow = build_sdxl_workflow(request, model)
    assert workflow["1"]["inputs"]["ckpt_name"] == "sdxl.safetensors"
    assert workflow["2"]["inputs"]["text"] == "glass perfume bottle"
    assert workflow["3"]["inputs"]["text"] == "text, watermark"
    assert workflow["5"]["inputs"]["seed"] == 123
    assert workflow["5"]["inputs"]["sampler_name"] == "euler"
    assert workflow["5"]["inputs"]["scheduler"] == "simple"
    assert workflow["5"]["inputs"]["steps"] == 26
    assert workflow["5"]["inputs"]["cfg"] == 5.0
    assert workflow["4"]["inputs"]["width"] == 1024


def test_commercial_generation_excludes_unverified_model(tmp_path):
    record = installed_model(tmp_path).model_copy(update={"license": ""})
    with pytest.raises(ValueError, match="commercial"):
        resolve_checkpoint(Registry(records=[record]), "sdxl-base-1.0", commercial=True)


def test_commercial_generation_requires_matching_license_record(tmp_path):
    model = installed_model(tmp_path)
    licenses = LicenseRegistry(records=[LicenseRecord(
        resource_id=model.id, license="Different license", commercial_use="allowed",
        source=model.source, last_verified="2026-09-25",
    )])
    with pytest.raises(ValueError, match="license registry"):
        resolve_checkpoint(Registry(records=[model]), model.id, commercial=True, licenses=licenses)


def test_generation_rejects_missing_checkpoint(tmp_path):
    record = installed_model(tmp_path).model_copy(update={"local_path": str(tmp_path / "missing.safetensors")})
    with pytest.raises(FileNotFoundError):
        resolve_checkpoint(Registry(records=[record]), "sdxl-base-1.0", commercial=False)


def test_qc_checks_dimensions_and_blank_output(tmp_path):
    valid = tmp_path / "valid.png"
    image = Image.new("RGB", (64, 64), "white")
    image.putpixel((0, 0), (0, 0, 0))
    image.save(valid)
    assert check_generated_image(valid, width=64, height=64).passed
    blank = tmp_path / "blank.png"
    Image.new("RGB", (64, 64), "white").save(blank)
    assert not check_generated_image(blank, width=64, height=64).passed
    assert not check_generated_image(valid, width=128, height=64).passed
