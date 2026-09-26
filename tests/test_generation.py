from pathlib import Path

import pytest
from PIL import Image

from ai_image_automation.generation import GenerationRequest, build_flux2_klein_workflow, build_sdxl_workflow, resolve_checkpoint
from ai_image_automation.quality.image_qc import check_generated_image
from ai_image_automation.registry import LicenseRecord, LicenseRegistry, ModelRecord, Registry, load_registry


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
    assert workflow["3"]["inputs"]["text"].startswith("text, watermark, ")
    assert "logo" in workflow["3"]["inputs"]["text"]
    assert "brand mark" in workflow["3"]["inputs"]["text"]
    assert workflow["5"]["inputs"]["seed"] == 123
    assert workflow["5"]["inputs"]["sampler_name"] == "euler"
    assert workflow["5"]["inputs"]["scheduler"] == "simple"
    assert workflow["5"]["inputs"]["steps"] == 26
    assert workflow["5"]["inputs"]["cfg"] == 5.0
    assert workflow["4"]["inputs"]["width"] == 1024


def test_stock_negative_prompt_applies_when_request_has_no_extra_terms(tmp_path):
    workflow = build_sdxl_workflow(GenerationRequest(prompt="plain ceramic mug"), installed_model(tmp_path))
    assert "logo" in workflow["3"]["inputs"]["text"]
    assert "watermark" in workflow["3"]["inputs"]["text"]


def test_klein_production_workflow_uses_registered_components_and_fixed_distilled_settings():
    root = Path(__file__).resolve().parents[1]
    models = {model.id: model for model in load_registry(root / "data" / "model_registry.json").records}
    request = GenerationRequest(prompt="one plain red apple on white", steps=4, cfg=1, seed=19,
                                sampler_name="euler", scheduler="Flux2Scheduler")
    workflow = build_flux2_klein_workflow(
        request, models["flux2-klein-4b-fp8"], models["flux2-klein-qwen3-4b-fp4"], models["flux2-klein-vae"]
    )
    assert workflow["1"]["inputs"]["unet_name"] == "flux-2-klein-4b-fp8.safetensors"
    assert workflow["2"]["inputs"]["clip_name"] == "qwen_3_4b_fp4_flux2.safetensors"
    assert workflow["3"]["inputs"]["vae_name"] == "flux2-vae.safetensors"
    assert workflow["8"]["inputs"]["steps"] == 4
    assert workflow["9"]["inputs"]["noise_seed"] == 19
    assert "no visible text" in workflow["4"]["inputs"]["text"]
    with pytest.raises(ValueError, match="4 steps"):
        build_flux2_klein_workflow(request.model_copy(update={"steps": 26}),
                                   models["flux2-klein-4b-fp8"], models["flux2-klein-qwen3-4b-fp4"], models["flux2-klein-vae"])


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
