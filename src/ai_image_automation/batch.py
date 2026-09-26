"""Frozen batch planning and resumable file-level execution."""

from __future__ import annotations

import hashlib
import json
import os
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ai_image_automation.research_cache import ResearchContext
from ai_image_automation.router import build_plan, freeze_plan, parse_intent, run_plan


class BatchItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")
    request: dict[str, Any]


class BatchManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    max_attempts: int = Field(default=2, ge=1, le=3)
    items: list[BatchItem] = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def unique_items(self) -> "BatchManifest":
        if self.schema_version != 1:
            raise ValueError("Unsupported batch manifest schema")
        names = [item.id for item in self.items]
        if len(set(names)) != len(names):
            raise ValueError("Duplicate batch item id")
        return self


def _digest(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]


def build_batch_plan(manifest: BatchManifest, context: ResearchContext, *, as_of: date | None = None) -> dict:
    """Validate every item before any batch plan is persisted."""
    items = [
        {"id": item.id, "plan": build_plan(parse_intent(item.request), context, as_of=as_of)}
        for item in manifest.items
    ]
    payload = {
        "schema_version": 1,
        "max_attempts": manifest.max_attempts,
        "items": items,
        "stock_review_required": ["visible_text", "logo", "branding"],
    }
    return {"batch_id": _digest(payload), **payload}


def freeze_batch(plan: dict, batches_dir: Path) -> Path:
    destination = batches_dir / plan["batch_id"] / "batch_plan.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(plan, indent=2, ensure_ascii=False) + "\n"
    try:
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if json.loads(destination.read_text(encoding="utf-8")) != plan:
            raise ValueError("Existing frozen batch plan differs")
    else:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(serialized)
    return destination


def load_batch(path: Path) -> dict:
    plan = json.loads(path.read_text(encoding="utf-8"))
    payload = {key: value for key, value in plan.items() if key != "batch_id"}
    if plan.get("schema_version") != 1 or plan.get("batch_id") != _digest(payload):
        raise ValueError("Frozen batch plan hash mismatch")
    BatchManifest.model_validate({
        "schema_version": 1, "max_attempts": plan["max_attempts"],
        "items": [{"id": item["id"], "request": item["plan"]["request"]} for item in plan["items"]],
    })
    for item in plan["items"]:
        child = item["plan"]
        if child.get("plan_id") != _digest({key: value for key, value in child.items() if key != "plan_id"}):
            raise ValueError(f"Frozen item plan hash mismatch: {item['id']}")
    return plan


def _write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


@contextmanager
def _batch_lock(batch_dir: Path):
    """An OS-held lock releases automatically after process interruption."""
    lock_path = batch_dir / "run.lock"
    with lock_path.open("a+b") as stream:
        stream.seek(0)
        if stream.read(1) != b"1":
            stream.seek(0)
            stream.write(b"1")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt

            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError("Batch is already running") from exc
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise RuntimeError("Batch is already running") from exc
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _retryable(exc: Exception) -> bool:
    if not isinstance(exc, RuntimeError):
        return False
    message = str(exc).lower()
    return any(term in message for term in (
        "timed out", "timeout", "connection refused", "connection reset",
        "temporarily unavailable", "cuda out of memory",
    ))


def _state_path(batch_dir: Path, item_id: str) -> Path:
    return batch_dir / "items" / f"{item_id}.json"


def _load_state(batch_dir: Path, item_id: str, plan_id: str) -> dict:
    path = _state_path(batch_dir, item_id)
    if path.is_file():
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("plan_id") != plan_id or state.get("id") != item_id:
            raise ValueError(f"Item checkpoint differs from frozen plan: {item_id}")
        if state.get("status") not in {
            "pending", "running", "pending_retry", "completed_requires_review", "manual_review_required", "failed",
        } or not isinstance(state.get("attempts"), int) or state["attempts"] < 0:
            raise ValueError(f"Invalid item checkpoint: {item_id}")
        return state
    return {
        "id": item_id, "plan_id": plan_id, "status": "pending", "attempts": 0,
        "total_attempts": 0, "outputs": [], "error_code": None,
        "error_type": None, "retryable": False,
    }


def batch_report(plan: dict, batch_dir: Path) -> dict:
    items = [_load_state(batch_dir, item["id"], item["plan"]["plan_id"]) for item in plan["items"]]
    counts = {status: sum(item["status"] == status for item in items) for status in (
        "pending", "running", "pending_retry", "completed_requires_review", "manual_review_required", "failed",
    )}
    finished = counts["completed_requires_review"] + counts["manual_review_required"] + counts["failed"]
    return {
        "batch_id": plan["batch_id"], "total": len(items), "counts": counts,
        "finished": finished, "progress_percent": round(100 * finished / len(items), 1),
        "stock_review_required": plan["stock_review_required"],
        "items": items,
    }


def _checkpoint(plan: dict, batch_dir: Path, state: dict) -> dict:
    _write_json(_state_path(batch_dir, state["id"]), state)
    report = batch_report(plan, batch_dir)
    _write_json(batch_dir / "progress.json", {key: value for key, value in report.items() if key != "items"})
    _write_json(batch_dir / "report.json", report)
    with (batch_dir / "events.jsonl").open("a", encoding="utf-8") as stream:
        item_index = next(index for index, item in enumerate(plan["items"]) if item["id"] == state["id"])
        stream.write(json.dumps({
            "batch_id": plan["batch_id"], "item_index": item_index, "plan_id": state["plan_id"],
            "status": state["status"], "attempts": state["attempts"],
        }) + "\n")
    return report


def _execute_child(plan: dict, batch_dir: Path, root: Path) -> dict:
    child_path = freeze_plan(plan, batch_dir / "child_jobs")
    return run_plan(child_path, root=root)


def run_batch(
    path: Path, *, root: Path,
    execute: Callable[[dict, Path, Path], dict] = _execute_child,
    retry_delay: Callable[[float], None] = time.sleep,
    on_progress: Callable[[dict], None] | None = None,
    retry_failed: bool = False,
) -> dict:
    plan = load_batch(path)
    batch_dir = path.parent
    with _batch_lock(batch_dir):
        for item in plan["items"]:
            state = _load_state(batch_dir, item["id"], item["plan"]["plan_id"])
            if state["status"] in ("completed_requires_review", "manual_review_required"):
                outputs_present = (
                    state["status"] == "manual_review_required" and not state["outputs"]
                    or bool(state["outputs"]) and all(Path(output).is_file() for output in state["outputs"])
                )
                if outputs_present:
                    continue
                if state["attempts"] >= plan["max_attempts"]:
                    state.update(
                        status="failed", outputs=[], error_code="missing_completed_output",
                        error_type=None, retryable=False,
                    )
                    report = _checkpoint(plan, batch_dir, state)
                    if on_progress:
                        on_progress(report)
                    continue
                state.update(status="pending_retry", outputs=[])
            if state["status"] == "failed" and retry_failed:
                state.update(
                    status="pending_retry", attempts=0, outputs=[],
                    error_code=None, error_type=None, retryable=False,
                )
            if state["status"] == "failed":
                continue
            recovering_running = state["status"] == "running"
            if not recovering_running and state["attempts"] >= plan["max_attempts"]:
                state.update(status="failed", error_code="attempts_exhausted", error_type=None, retryable=False)
                report = _checkpoint(plan, batch_dir, state)
                if on_progress:
                    on_progress(report)
                continue
            while recovering_running or state["attempts"] < plan["max_attempts"]:
                if not recovering_running:
                    state["attempts"] += 1
                    state["total_attempts"] = state.get("total_attempts", 0) + 1
                recovering_running = False
                state["status"] = "running"
                report = _checkpoint(plan, batch_dir, state)
                if on_progress:
                    on_progress(report)
                try:
                    result = execute(item["plan"], batch_dir, root)
                    if result["status"] not in ("completed_requires_review", "manual_review_required"):
                        raise ValueError("Unexpected child execution status")
                    outputs = result.get("outputs", [])
                    if result["status"] == "completed_requires_review":
                        if not outputs or not all(Path(output).is_file() for output in outputs):
                            raise ValueError("Completed child job has missing output")
                    elif outputs:
                        raise ValueError("Manual review route unexpectedly produced output")
                except Exception as exc:
                    state["retryable"] = _retryable(exc)
                    state["error_code"] = (
                        "transient_execution_failure" if state["retryable"] else "plan_or_execution_failure"
                    )
                    state["error_type"] = type(exc).__name__
                    state["status"] = (
                        "pending_retry" if state["retryable"] and state["attempts"] < plan["max_attempts"]
                        else "failed"
                    )
                    report = _checkpoint(plan, batch_dir, state)
                    if on_progress:
                        on_progress(report)
                    if state["status"] != "pending_retry":
                        break
                    retry_delay(min(2 ** (state["attempts"] - 1), 4))
                    continue
                state.update(
                    status=result["status"], outputs=result.get("outputs", []),
                    error_code=None, error_type=None, retryable=False,
                )
                report = _checkpoint(plan, batch_dir, state)
                if on_progress:
                    on_progress(report)
                break
        report = batch_report(plan, batch_dir)
        _write_json(batch_dir / "report.json", report)
        _write_json(batch_dir / "progress.json", {key: value for key, value in report.items() if key != "items"})
        return report
