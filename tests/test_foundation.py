import json
import logging

import pytest

from ai_image_automation.config import load_settings
from ai_image_automation.registry import (
    LicenseRegistry, ModelRecord, Registry, ResearchCache, ToolRegistry,
    load_registry,
)
from ai_image_automation.logging_setup import configure_logging


def test_default_and_8gb_config_load():
    settings = load_settings()
    assert settings.hardware.target_vram_gb == 8
    assert settings.comfyui.base_url == "http://127.0.0.1:8188"
    assert settings.generation.width == 1024
    assert settings.generation.steps == 4
    assert settings.generation.sampler_name == "euler"
    assert settings.generation.scheduler == "Flux2Scheduler"


def test_config_rejects_excessive_target_vram(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("hardware:\n  target_vram_gb: 12\n  available_vram_gb: 8\n", encoding="utf-8")
    with pytest.raises(ValueError, match="target_vram_gb"):
        load_settings(path)


def test_config_rejects_unknown_keys(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("generation:\n  unexpected_option: 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unexpected_option"):
        load_settings(path)


def test_registry_excludes_unclear_license_for_commercial_use(tmp_path):
    path = tmp_path / "models.json"
    path.write_text(json.dumps({"schema_version": 1, "records": [
        {"id": "unknown", "name": "Unknown", "tasks": ["generate"], "commercial_use": "unclear"},
        {"id": "ok", "name": "OK", "tasks": ["generate"], "commercial_use": "allowed", "installed": True,
         "license": "Apache-2.0", "source": "https://example.org/official", "last_verified": "2026-09-25"}
    ]}), encoding="utf-8")
    registry = load_registry(path)
    assert [record.id for record in registry.eligible("generate", commercial=True)] == ["ok"]


def test_commercial_eligibility_requires_license_evidence():
    registry = Registry(records=[ModelRecord(id="unverified", name="Unverified", tasks=["generate"], commercial_use="allowed")])
    assert registry.eligible("generate", commercial=True) == []


def test_registry_rejects_duplicate_ids():
    record = ModelRecord(id="same", name="Same")
    with pytest.raises(ValueError, match="duplicate"):
        Registry(records=[record, record])


def test_all_shipped_registries_validate():
    from pathlib import Path

    data = Path(__file__).resolve().parents[1] / "data"
    model_records = load_registry(data / "model_registry.json").records
    assert [record.id for record in model_records] == [
        "sdxl-base-1.0", "flux2-klein-4b-fp8", "flux2-klein-qwen3-4b-fp4", "flux2-klein-vae",
    ]
    assert model_records[0].installed is True
    upscalers = load_registry(data / "upscaler_registry.json").records
    controlnets = load_registry(data / "controlnet_registry.json").records
    assert [record.id for record in upscalers] == ["realesrgan-x2plus", "realesrgan-x4plus"]
    assert [record.id for record in controlnets] == ["xinsir-tile-sdxl-1.0"]
    assert upscalers[0].installed and controlnets[0].installed
    backgrounds = load_registry(data / "background_registry.json")
    assert [record.id for record in backgrounds.eligible("remove_background", commercial=True)] == [
        "birefnet-dis", "ben2-base",
    ]
    assert all(record.installed and record.sha256 for record in backgrounds.eligible("remove_background", commercial=True))
    assert backgrounds.records[-1].id == "bria-rmbg-2.0"
    assert backgrounds.records[-1].commercial_use == "restricted"
    licenses = LicenseRegistry.model_validate_json((data / "license_registry.json").read_text(encoding="utf-8")).records
    tools = ToolRegistry.model_validate_json((data / "tool_registry.json").read_text(encoding="utf-8")).records
    assert [record.resource_id for record in licenses] == [
        "comfyui", "sdxl-base-1.0", "flux2-klein-4b-fp8", "flux2-klein-qwen3-4b-fp4", "flux2-klein-vae",
        "realesrgan-x2plus", "realesrgan-x4plus", "xinsir-tile-sdxl-1.0", "ultimate-sd-upscale",
        "birefnet-dis", "ben2-base", "bria-rmbg-2.0",
    ]
    assert [record.id for record in tools] == ["comfyui", "ultimate-sd-upscale"]
    assert all(record.installed for record in tools)
    cached = ResearchCache.model_validate_json((data / "research_cache.json").read_text(encoding="utf-8")).entries
    assert {(entry.task, entry.subject_type) for entry in cached} == {
        ("creative_upscale", "product_refine"), ("creative_upscale_checkpoint", "sdxl"), ("generate", "isolated_object"),
        ("remove_background", "opaque_isolate"), ("remove_background", "glass_isolate"),
        ("remove_background", "translucent_isolate"), ("upscale", "pixel_2x"), ("upscale", "pixel_4x"),
    }


def test_model_checksum_must_be_sha256():
    with pytest.raises(ValueError, match="sha256"):
        ModelRecord(id="bad", name="Bad", sha256="123")


def test_logging_emits_structured_json_without_duplicate_handlers(tmp_path):
    logger = configure_logging(tmp_path / "run.jsonl")
    logger = configure_logging(tmp_path / "run.jsonl")
    logger.info("started", extra={"job_id": "abc"})
    lines = (tmp_path / "run.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["job_id"] == "abc"
    assert json.loads(lines[0])["message"] == "started"
    for handler in logger.handlers:
        handler.close()
    logger.handlers.clear()
