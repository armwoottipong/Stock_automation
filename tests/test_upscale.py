from pathlib import Path

import pytest
from PIL import Image

from ai_image_automation.comfyui.client import ComfyUIError
from ai_image_automation.registry import LicenseRecord, LicenseRegistry, ModelRecord, Registry
from ai_image_automation.upscale import (
    CreativeUpscaleRequest, UpscaleRequest, build_creative_workflow,
    build_pixel_workflow, make_guided_image, resolve_upscaler,
    run_creative_with_lowvram_retry, stage_input_image,
)


def model(tmp_path: Path) -> ModelRecord:
    path = tmp_path / "RealESRGAN_x2plus.pth"
    path.write_bytes(b"test")
    return ModelRecord(
        id="realesrgan-x2plus", name="RealESRGAN x2plus", category=["upscaler"],
        tasks=["upscale"], commercial_use="allowed", license="BSD-3-Clause",
        source="https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.1",
        last_verified="2026-09-25", installed=True, local_path=str(path),
    )


def test_stage_input_checks_integrity_and_uses_content_identity(tmp_path):
    source = tmp_path / "bottle.png"
    Image.new("RGB", (64, 96), "red").save(source)
    staged = stage_input_image(source, tmp_path / "comfy-input")
    assert staged.is_file()
    assert staged.name.startswith("upscale_")
    assert staged.read_bytes() == source.read_bytes()
    assert stage_input_image(source, staged.parent) == staged
    damaged = tmp_path / "damaged.png"
    damaged.write_bytes(b"not an image")
    with pytest.raises(ValueError, match="valid image"):
        stage_input_image(damaged, staged.parent)


def test_pixel_workflow_uses_registered_model_and_staged_image(tmp_path):
    request = UpscaleRequest(input=tmp_path / "source.png", scale=2)
    workflow = build_pixel_workflow(request, "upscale_abc.png", model(tmp_path))
    assert workflow["1"]["class_type"] == "LoadImage"
    assert workflow["1"]["inputs"]["image"] == "upscale_abc.png"
    assert workflow["2"]["inputs"]["model_name"] == "RealESRGAN_x2plus.pth"
    assert workflow["3"]["class_type"] == "ImageUpscaleWithModel"
    assert workflow["4"]["class_type"] == "SaveImage"


def test_upscaler_requires_matching_commercial_license_and_local_file(tmp_path):
    upscaler = model(tmp_path)
    registry = Registry(records=[upscaler])
    licenses = LicenseRegistry(records=[LicenseRecord(
        resource_id=upscaler.id, license=upscaler.license, commercial_use="allowed",
        source=upscaler.source, last_verified="2026-09-25",
    )])
    assert resolve_upscaler(registry, upscaler.id, commercial=True, licenses=licenses) == upscaler
    with pytest.raises(ValueError, match="license"):
        resolve_upscaler(registry, upscaler.id, commercial=True, licenses=LicenseRegistry())
    upscaler.local_path = str(tmp_path / "missing.pth")
    with pytest.raises(FileNotFoundError):
        resolve_upscaler(Registry(records=[upscaler]), upscaler.id, commercial=False)


def test_guided_image_keeps_shape_and_preserves_a_hard_boundary(tmp_path):
    source = tmp_path / "edge.png"
    image = Image.new("RGB", (64, 32), "black")
    for x in range(32, 64):
        for y in range(32):
            image.putpixel((x, y), (240, 240, 240))
    image.save(source)
    guided = tmp_path / "guided.png"
    make_guided_image(source, guided, radius=8, eps=0.001)
    with Image.open(guided) as result:
        assert result.size == image.size
        assert result.getpixel((30, 16))[0] < 25
        assert result.getpixel((33, 16))[0] > 215


def test_creative_workflow_injects_controlnet_and_tile_parameters(tmp_path):
    request = CreativeUpscaleRequest(
        input=tmp_path / "source.png", prompt="glass reflections",
        negative_prompt="text", seed=42, tile=768, padding=64,
        denoise=0.34, control_weight=0.88, control_end=0.75,
        seam_denoise=0.14, seam_mask_blur=16,
    )
    workflow = build_creative_workflow(
        request, image_name="source.png", guide_name="guided.png",
        checkpoint_name="sdxl.safetensors", controlnet_name="tile.safetensors",
    )
    assert workflow["1"]["inputs"]["image"] == "source.png"
    assert workflow["2"]["inputs"]["image"] == "guided.png"
    assert "logo" in workflow["5"]["inputs"]["text"]
    assert workflow["6"]["inputs"]["control_net_name"] == "tile.safetensors"
    assert workflow["7"]["inputs"]["strength"] == 0.88
    assert workflow["7"]["inputs"]["end_percent"] == 0.75
    assert workflow["8"]["inputs"]["tile_width"] == 768
    assert workflow["8"]["inputs"]["tile_padding"] == 64
    assert workflow["8"]["inputs"]["seam_fix_mode"] == "Half Tile"
    assert workflow["8"]["inputs"]["seam_fix_denoise"] == 0.14
    assert workflow["8"]["inputs"]["tiled_decode"] is True


def test_creative_oom_retries_once_with_smaller_tiles(tmp_path):
    request = CreativeUpscaleRequest(input=tmp_path / "source.png", prompt="refine", tile=768, padding=64)
    calls = []

    def run(workflow):
        calls.append(workflow)
        if len(calls) == 1:
            raise ComfyUIError("CUDA out of memory")
        return "completed"

    result, effective = run_creative_with_lowvram_retry(request, lambda req: {"tile": req.tile}, run)
    assert result == "completed"
    assert effective.tile == 512
    assert [call["tile"] for call in calls] == [768, 512]


def test_creative_does_not_retry_unrelated_error(tmp_path):
    request = CreativeUpscaleRequest(input=tmp_path / "source.png", prompt="refine")
    calls = []

    def run(workflow):
        calls.append(workflow)
        raise ComfyUIError("Invalid ControlNet model")

    with pytest.raises(ComfyUIError, match="Invalid ControlNet"):
        run_creative_with_lowvram_retry(request, lambda req: {"tile": req.tile}, run)
    assert len(calls) == 1
