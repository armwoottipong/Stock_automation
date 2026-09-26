import json
from pathlib import Path

from scripts.audit_output import audit


def approved_manifest(**overrides):
    value = {
        "status": "ready_to_submit",
        "platform": "adobe_stock",
        "source_type": "camera_photo",
        "checks": {"visual_review": True, "metadata": True, "technical": True, "rights": True},
        "assets": ["photo.jpg"],
    }
    value.update(overrides)
    return value


def test_empty_output_and_approved_package_pass(tmp_path: Path):
    (tmp_path / ".gitkeep").touch()
    assert audit(tmp_path) == []
    package = tmp_path / "approved"
    package.mkdir()
    (package / "photo.jpg").write_bytes(b"fixture")
    (package / "submission_manifest.json").write_text(json.dumps(approved_manifest()))
    assert audit(tmp_path) == []


def test_drafts_loose_files_and_ai_shutterstock_are_rejected(tmp_path: Path):
    (tmp_path / "draft.zip").write_bytes(b"fixture")
    package = tmp_path / "draft"
    package.mkdir()
    (package / "photo.jpg").write_bytes(b"fixture")
    (package / "submission_manifest.json").write_text(json.dumps(approved_manifest(
        platform="shutterstock", source_type="generative_ai", status="draft",
        checks={"visual_review": False, "metadata": True, "technical": True, "rights": True},
    )))
    errors = audit(tmp_path)
    assert any("Loose file" in error for error in errors)
    assert any("not approved" in error for error in errors)
    assert any("blocked for Shutterstock" in error for error in errors)
    assert any("reviews incomplete" in error for error in errors)


def test_invalid_manifest_is_rejected_without_crashing(tmp_path: Path):
    package = tmp_path / "invalid"
    package.mkdir()
    (package / "submission_manifest.json").write_text("[]")
    assert any("Invalid submission manifest" in error for error in audit(tmp_path))
