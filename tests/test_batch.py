import json
from datetime import date
from pathlib import Path

import pytest
from PIL import Image

from ai_image_automation.batch import (
    BatchManifest, batch_report, build_batch_plan, freeze_batch, load_batch, run_batch,
)
from ai_image_automation.research_cache import load_context


ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 9, 26)


def make_plan(tmp_path: Path, *, max_attempts: int = 2, subjects: tuple[str, ...] = ("opaque_isolate", "glass_isolate")) -> Path:
    source = tmp_path / "object.png"
    Image.new("RGB", (96, 96), "white").save(source)
    manifest = BatchManifest.model_validate({
        "max_attempts": max_attempts,
        "items": [
            {"id": f"item_{index}", "request": {
                "operation": "remove_background", "subject_type": subject,
                "input": str(source),
            }}
            for index, subject in enumerate(subjects)
        ],
    })
    plan = build_batch_plan(manifest, load_context(ROOT / "data"), as_of=AS_OF)
    return freeze_batch(plan, tmp_path / "batches")


def test_batch_plan_is_one_frozen_artifact_and_rejects_tampering(tmp_path: Path):
    path = make_plan(tmp_path)
    plan = load_batch(path)
    assert len(plan["items"]) == 2
    assert len({item["plan"]["plan_id"] for item in plan["items"]}) == 2
    assert freeze_batch(plan, tmp_path / "batches") == path
    changed = json.loads(path.read_text(encoding="utf-8"))
    changed["max_attempts"] = 3
    path.write_text(json.dumps(changed), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        load_batch(path)


def test_batch_checkpoints_each_file_and_resume_skips_completed(tmp_path: Path):
    path = make_plan(tmp_path)
    output = tmp_path / "result.png"
    output.write_bytes(b"image")
    calls = []

    def execute(plan, _batch_dir, _root):
        calls.append(plan["subject_type"])
        if plan["route"] == "manual_review":
            return {"status": "manual_review_required", "outputs": []}
        return {"status": "completed_requires_review", "outputs": [str(output)]}

    first = run_batch(path, root=ROOT, execute=execute, retry_delay=lambda _: None)
    assert first["progress_percent"] == 100.0
    assert first["counts"]["completed_requires_review"] == 1
    assert first["counts"]["manual_review_required"] == 1
    assert len(calls) == 2
    assert run_batch(path, root=ROOT, execute=execute, retry_delay=lambda _: None) == first
    assert len(calls) == 2
    assert (path.parent / "progress.json").is_file()
    assert (path.parent / "report.json").is_file()
    assert len((path.parent / "events.jsonl").read_text(encoding="utf-8").splitlines()) == 4


def test_transient_failure_retries_only_one_file(tmp_path: Path):
    path = make_plan(tmp_path, subjects=("glass_isolate",))
    calls = 0
    delays = []

    def execute(_plan, _batch_dir, _root):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("Connection reset by peer")
        return {"status": "manual_review_required", "outputs": []}

    report = run_batch(path, root=ROOT, execute=execute, retry_delay=delays.append)
    assert calls == 2
    assert delays == [1]
    assert report["items"][0]["attempts"] == 2
    assert report["items"][0]["total_attempts"] == 2
    assert report["items"][0]["status"] == "manual_review_required"


def test_permanent_failure_is_reported_and_later_files_continue(tmp_path: Path):
    path = make_plan(tmp_path)
    calls = []

    def execute(plan, _batch_dir, _root):
        calls.append(plan["subject_type"])
        if plan["subject_type"] == "opaque_isolate":
            raise ValueError("model changed")
        return {"status": "manual_review_required", "outputs": []}

    report = run_batch(path, root=ROOT, execute=execute, retry_delay=lambda _: None)
    assert calls == ["opaque_isolate", "glass_isolate"]
    assert report["counts"]["failed"] == 1
    assert report["counts"]["manual_review_required"] == 1
    assert report["items"][0]["error_code"] == "plan_or_execution_failure"
    assert report["items"][0]["error_type"] == "ValueError"
    assert "model changed" not in json.dumps(report)
    assert batch_report(load_batch(path), path.parent) == report


def test_interrupted_running_item_resumes_same_attempt(tmp_path: Path):
    path = make_plan(tmp_path, max_attempts=1, subjects=("glass_isolate",))

    def interrupt(_plan, _batch_dir, _root):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        run_batch(path, root=ROOT, execute=interrupt, retry_delay=lambda _: None)
    assert batch_report(load_batch(path), path.parent)["items"][0]["status"] == "running"
    report = run_batch(
        path, root=ROOT,
        execute=lambda *_: {"status": "manual_review_required", "outputs": []},
        retry_delay=lambda _: None,
    )
    assert report["items"][0]["attempts"] == 1
    assert report["items"][0]["total_attempts"] == 1
    assert report["progress_percent"] == 100.0


def test_failed_item_requires_explicit_retry_round(tmp_path: Path):
    path = make_plan(tmp_path, max_attempts=1, subjects=("glass_isolate",))
    calls = 0

    def execute(_plan, _batch_dir, _root):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ValueError("invalid input")
        return {"status": "manual_review_required", "outputs": []}

    first = run_batch(path, root=ROOT, execute=execute, retry_delay=lambda _: None)
    assert first["counts"]["failed"] == 1
    run_batch(path, root=ROOT, execute=execute, retry_delay=lambda _: None)
    assert calls == 1
    retried = run_batch(path, root=ROOT, execute=execute, retry_delay=lambda _: None, retry_failed=True)
    assert retried["counts"]["manual_review_required"] == 1
    assert retried["items"][0]["total_attempts"] == 2


def test_missing_completed_output_is_reported(tmp_path: Path):
    path = make_plan(tmp_path, max_attempts=1, subjects=("opaque_isolate",))
    output = tmp_path / "result.png"
    output.write_bytes(b"image")
    run_batch(
        path, root=ROOT,
        execute=lambda *_: {"status": "completed_requires_review", "outputs": [str(output)]},
        retry_delay=lambda _: None,
    )
    output.unlink()
    report = run_batch(path, root=ROOT, execute=lambda *_: pytest.fail("must not rerun"), retry_delay=lambda _: None)
    assert report["items"][0]["status"] == "failed"
    assert report["items"][0]["error_code"] == "missing_completed_output"
    assert report["items"][0]["outputs"] == []


def test_duplicate_ids_rejected_before_planning():
    with pytest.raises(ValueError, match="Duplicate batch item id"):
        BatchManifest.model_validate({"items": [
            {"id": "same", "request": {}}, {"id": "same", "request": {}},
        ]})
