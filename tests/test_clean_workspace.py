import json
from pathlib import Path

from scripts.audit_output import audit
from scripts.clean_workspace import clean_comfyui, clean_job_images, clean_staging, clean_workspace


def test_clean_staging_only_removes_audited_sets(tmp_path: Path):
    staging = tmp_path / "staging"
    output = tmp_path / "output"
    staging.mkdir()
    output.mkdir()

    # Set 1: audited and delivered
    set1_stg = staging / "set_001"
    set1_stg.mkdir()
    (set1_stg / "image.png").write_bytes(b"x" * 100)

    set1_out = output / "set_001"
    set1_out.mkdir()
    (set1_out / "set_manifest.json").write_text(json.dumps({"set_id": "set_001", "packages": ["pkg1"]}))
    pkg1 = set1_out / "pkg1"
    pkg1.mkdir()
    (pkg1 / "photo.jpg").write_bytes(b"photo")
    (pkg1 / "submission_manifest.json").write_text(json.dumps({
        "platform": "adobe_stock", "source_type": "camera_photo",
        "checks": {"metadata": True, "technical": True, "rights": True},
        "assets": ["photo.jpg"],
    }))

    # Set 2: not in output (in progress)
    set2_stg = staging / "set_002"
    set2_stg.mkdir()
    (set2_stg / "wip.png").write_bytes(b"wip")

    # Dry-run preview
    preview = clean_staging(tmp_path, apply=False)
    assert preview["count"] == 1
    assert preview["items"][0]["set_id"] == "set_001"
    assert set1_stg.exists()
    assert set2_stg.exists()

    # Apply
    applied = clean_staging(tmp_path, apply=True)
    assert applied["count"] == 1
    assert not set1_stg.exists()
    assert set2_stg.exists()


def test_clean_comfyui_cache(tmp_path: Path):
    comfy_out = tmp_path / "vendor" / "ComfyUI" / "output"
    comfy_temp = tmp_path / "vendor" / "ComfyUI" / "temp"
    comfy_out.mkdir(parents=True)
    comfy_temp.mkdir(parents=True)

    (comfy_out / "render1.png").write_bytes(b"x" * 50)
    (comfy_temp / "temp1.png").write_bytes(b"x" * 50)
    (comfy_out / ".keep").write_bytes(b"keep")

    preview = clean_comfyui(tmp_path, apply=False)
    assert preview["file_count"] == 2
    assert preview["reclaimed_bytes"] == 100
    assert (comfy_out / "render1.png").exists()

    applied = clean_comfyui(tmp_path, apply=True)
    assert applied["file_count"] == 2
    assert not (comfy_out / "render1.png").exists()
    assert not (comfy_temp / "temp1.png").exists()
    assert (comfy_out / ".keep").exists()


def test_clean_job_images_preserves_metadata(tmp_path: Path):
    jobs = tmp_path / "jobs" / "job_123"
    jobs.mkdir(parents=True)

    (jobs / "rendered.png").write_bytes(b"image_bytes")
    (jobs / "request.json").write_text("{\"op\": \"generate\"}")
    (jobs / "execution.json").write_text("{\"status\": \"ok\"}")

    preview = clean_job_images(tmp_path, apply=False)
    assert preview["file_count"] == 1
    assert (jobs / "rendered.png").exists()

    applied = clean_job_images(tmp_path, apply=True)
    assert applied["file_count"] == 1
    assert not (jobs / "rendered.png").exists()
    assert (jobs / "request.json").exists()
    assert (jobs / "execution.json").exists()
