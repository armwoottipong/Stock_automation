import json
from types import SimpleNamespace
from datetime import date
from pathlib import Path

import pytest
from PIL import Image

from ai_image_automation.generation import GenerationRequest, build_sdxl_workflow
from ai_image_automation.research_cache import load_context
from ai_image_automation.router import (
    _command, build_plan, freeze_plan, load_plan, parse_intent, run_plan,
)


ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 9, 25)


def test_generate_plan_freezes_stock_prompt_and_registered_selection(tmp_path: Path):
    intent = parse_intent({"operation": "generate", "description": "blue ceramic mug", "seed": 12})
    context = load_context(ROOT / "data")
    plan = build_plan(intent, context, as_of=AS_OF)
    assert plan["workflow"] == "generate_sdxl"
    assert plan["models"]["checkpoint"]["id"] == "sdxl-base-1.0"
    assert "pure white seamless background" in plan["request"]["prompt"]
    assert "logo" in plan["request"]["negative_prompt"]
    assert "brand mark" in plan["request"]["negative_prompt"]
    assert plan["request"]["seed"] == 12
    assert plan["workflow_template"]["path"] == "workflows/templates/generate_sdxl.json"
    workflow = build_sdxl_workflow(GenerationRequest(**plan["request"]), context.models["sdxl-base-1.0"])
    assert workflow["3"]["inputs"]["text"] == plan["request"]["negative_prompt"]
    path = freeze_plan(plan, tmp_path)
    assert freeze_plan(plan, tmp_path) == path
    assert load_plan(path) == plan
    changed = json.loads(path.read_text(encoding="utf-8"))
    changed["request"]["seed"] = 13
    path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_plan(path)


def test_router_rejects_brand_requests_and_stale_research():
    context = load_context(ROOT / "data")
    branded = parse_intent({"operation": "generate", "description": "mug with logo"})
    with pytest.raises(ValueError, match="text or branding"):
        build_plan(branded, context, as_of=AS_OF)
    plain = parse_intent({"operation": "generate", "description": "blue mug"})
    with pytest.raises(ValueError, match="No fresh reviewed research"):
        build_plan(plain, context, as_of=date(2026, 10, 26))


def test_glass_plan_routes_to_review_without_inference(tmp_path: Path):
    source = tmp_path / "glass.png"
    Image.new("RGB", (96, 96), "white").save(source)
    intent = parse_intent({"operation": "remove_background", "subject_type": "glass_isolate", "input": str(source)})
    plan = build_plan(intent, load_context(ROOT / "data"), as_of=AS_OF)
    assert plan["route"] == "manual_review"
    assert plan["models"] == {}
    path = freeze_plan(plan, tmp_path / "jobs")
    record = run_plan(path, root=ROOT, as_of=AS_OF)
    assert record["status"] == "manual_review_required"
    assert record["outputs"] == []
    execution_file = path.parent / "execution.json"
    execution_file.write_text(json.dumps({"plan_id": "wrong", "status": "completed_requires_review", "outputs": []}), encoding="utf-8")
    recovered = run_plan(path, root=ROOT, as_of=AS_OF)
    assert recovered == record
    assert json.loads(execution_file.read_text(encoding="utf-8")) == record


def test_execution_failure_does_not_expose_subprocess_stderr(tmp_path: Path, monkeypatch):
    source = tmp_path / "object.png"
    Image.new("RGB", (96, 96), "white").save(source)
    plan = build_plan(
        parse_intent({"operation": "remove_background", "subject_type": "opaque_isolate", "input": str(source)}),
        load_context(ROOT / "data"), as_of=AS_OF,
    )
    path = freeze_plan(plan, tmp_path / "jobs")
    import ai_image_automation.router as router

    original_hash = router.sha256_file
    monkeypatch.setattr(router, "sha256_file", lambda target: (
        plan["models"]["background"]["sha256"] if str(target).endswith("birefnet-dis/model.safetensors") or str(target).endswith("birefnet-dis\\model.safetensors")
        else original_hash(target)
    ))
    monkeypatch.setattr(router, "_command", lambda *_: ["fake-worker"])
    monkeypatch.setattr(router.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(
        returncode=1, stderr="secret-token prompt text: CUDA out of memory", stdout="",
    ))
    with pytest.raises(RuntimeError, match="CUDA out of memory") as exc:
        run_plan(path, root=ROOT, as_of=AS_OF)
    assert "secret-token" not in str(exc.value)


def test_input_change_blocks_frozen_pixel_plan(tmp_path: Path):
    source = tmp_path / "mug.png"
    Image.new("RGB", (96, 96), "white").save(source)
    plan = build_plan(
        parse_intent({"operation": "upscale", "input": str(source)}),
        load_context(ROOT / "data"), as_of=date(2026, 9, 26),
    )
    assert plan["models"]["upscaler"]["id"] == "realesrgan-x4plus"
    assert plan["request"]["scale"] == 4
    path = freeze_plan(plan, tmp_path / "jobs")
    Image.new("RGB", (96, 96), "black").save(source)
    with pytest.raises(ValueError, match="Input image changed"):
        run_plan(path, root=ROOT, as_of=date(2026, 9, 26))


def test_explicit_2x_plan_keeps_legacy_model(tmp_path: Path):
    source = tmp_path / "mug.png"
    Image.new("RGB", (96, 96), "white").save(source)
    intent = parse_intent({"operation": "upscale", "input": str(source), "scale": 2})
    plan = build_plan(intent, load_context(ROOT / "data"), as_of=date(2026, 9, 26))
    assert plan["subject_type"] == "pixel_2x"
    assert plan["request"]["scale"] == 2
    assert plan["models"]["upscaler"]["id"] == "realesrgan-x2plus"
    assert _command(plan, ROOT)[-2:] == ["--scale", "2"]


def test_creative_plan_carries_all_effective_parameters(tmp_path: Path):
    source = tmp_path / "source.png"
    Image.new("RGB", (96, 96), "blue").save(source)
    intent = parse_intent({
        "operation": "creative_upscale", "input": str(source), "prompt": "refine ceramic edges",
        "seed": 11, "tile": 512, "sampler_name": "euler", "scheduler": "simple",
    })
    plan = build_plan(intent, load_context(ROOT / "data"), as_of=AS_OF)
    assert plan["models"]["checkpoint"]["id"] == "sdxl-base-1.0"
    assert plan["models"]["controlnet"]["id"] == "xinsir-tile-sdxl-1.0"
    command = _command(plan, ROOT)
    assert command[command.index("--sampler-name") + 1] == "euler"
    assert command[command.index("--scheduler") + 1] == "simple"
    assert command[command.index("--tile") + 1] == "512"
    assert plan["retry_policy"] is None
    larger = parse_intent({
        "operation": "creative_upscale", "input": str(source), "prompt": "refine ceramic edges", "tile": 768,
    })
    assert build_plan(larger, load_context(ROOT / "data"), as_of=AS_OF)["retry_policy"]["tile"] == 512
