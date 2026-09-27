import json
from pathlib import Path

from scripts.audit_output import audit


def production_manifest(**overrides):
    value = {
        "platform": "adobe_stock",
        "source_type": "camera_photo",
        "checks": {"metadata": True, "technical": True, "rights": True},
        "assets": ["photo.jpg"],
    }
    value.update(overrides)
    return value


def test_empty_output_and_production_package_pass(tmp_path: Path):
    (tmp_path / ".gitkeep").touch()
    assert audit(tmp_path) == []
    package = tmp_path / "delivery"
    package.mkdir()
    (package / "photo.jpg").write_bytes(b"fixture")
    (package / "submission_manifest.json").write_text(json.dumps(production_manifest()))
    assert audit(tmp_path) == []


def test_drafts_loose_files_and_ai_shutterstock_are_rejected(tmp_path: Path):
    (tmp_path / "draft.zip").write_bytes(b"fixture")
    package = tmp_path / "draft"
    package.mkdir()
    (package / "photo.jpg").write_bytes(b"fixture")
    (package / "submission_manifest.json").write_text(json.dumps(production_manifest(
        platform="shutterstock", source_type="generative_ai", status="draft",
    )))
    errors = audit(tmp_path)
    assert any("Loose file" in error for error in errors)
    assert any("Review-status field" in error for error in errors)
    assert any("blocked for Shutterstock" in error for error in errors)


def test_invalid_manifest_is_rejected_without_crashing(tmp_path: Path):
    package = tmp_path / "invalid"
    package.mkdir()
    (package / "submission_manifest.json").write_text("[]")
    assert any("Invalid submission manifest" in error for error in audit(tmp_path))


def test_production_package_rejects_visual_review_fields(tmp_path: Path):
    package = tmp_path / "delivery"
    package.mkdir()
    (package / "photo.jpg").write_bytes(b"fixture")
    manifest = production_manifest(checks={
        "visual_review": False, "metadata": True, "technical": True, "rights": True,
    }, visual_review_owner="user")
    (package / "submission_manifest.json").write_text(json.dumps(manifest))
    errors = audit(tmp_path)
    assert any("Visual-review check" in error for error in errors)
    assert any("Review-status field" in error for error in errors)


def test_required_deterministic_checks_still_apply(tmp_path: Path):
    package = tmp_path / "delivery"
    package.mkdir()
    (package / "photo.jpg").write_bytes(b"fixture")
    manifest = production_manifest(checks={"metadata": True, "technical": False, "rights": True})
    (package / "submission_manifest.json").write_text(json.dumps(manifest))
    assert any("Required checks incomplete" in error for error in audit(tmp_path))


def test_local_white_png_companion_is_not_an_adobe_package(tmp_path: Path):
    package = tmp_path / "white_png"
    package.mkdir()
    (package / "apple_white.png").write_bytes(b"fixture")
    manifest = production_manifest(
        platform="local_delivery", package_purpose="white_png_companion",
        source_type="generative_ai", assets=["apple_white.png"],
    )
    (package / "submission_manifest.json").write_text(json.dumps(manifest))
    assert audit(tmp_path) == []
    del manifest["package_purpose"]
    (package / "submission_manifest.json").write_text(json.dumps(manifest))
    assert any("Invalid local delivery purpose" in error for error in audit(tmp_path))
