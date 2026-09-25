"""Deterministic job identity, checkpoints, and resume."""

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol

from ai_image_automation.comfyui.client import ComfyUIError
from ai_image_automation.logging_setup import configure_logging


class ClientProtocol(Protocol):
    def queue_workflow(self, workflow: dict[str, Any]) -> str: ...
    def wait_for_completion(self, prompt_id: str, **kwargs: Any) -> dict[str, Any]: ...
    def download_outputs(self, history: dict[str, Any], output_dir: Path) -> list[Path]: ...


@dataclass
class JobRecord:
    job_id: str
    status: str = "pending"
    prompt_id: str | None = None
    outputs: list[str] = field(default_factory=list)
    error: str | None = None


class JobRunner:
    def __init__(self, client: ClientProtocol, jobs_dir: Path):
        self.client = client
        self.jobs_dir = jobs_dir

    @staticmethod
    def identity(workflow: dict[str, Any]) -> str:
        canonical = json.dumps(workflow, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _write_json(path: Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, path)

    def run(self, workflow: dict[str, Any]) -> JobRecord:
        job_id = self.identity(workflow)
        job_dir = self.jobs_dir / job_id
        job_file = job_dir / "job.json"
        workflow_file = job_dir / "workflow.json"
        logger = configure_logging(job_dir / "logs" / "runtime.jsonl")

        if job_file.exists():
            record = JobRecord(**json.loads(job_file.read_text(encoding="utf-8")))
            if not workflow_file.exists() or json.loads(workflow_file.read_text(encoding="utf-8")) != workflow:
                raise ValueError(f"Workflow changed for existing job {job_id}")
        else:
            record = JobRecord(job_id=job_id)
            self._write_json(workflow_file, workflow)
            self._write_json(job_file, asdict(record))

        if record.status == "completed":
            if all(Path(path).exists() for path in record.outputs):
                return record
            raise ComfyUIError(f"Completed job {job_id} has missing output files")
        if record.status == "failed":
            raise ComfyUIError(f"Job {job_id} previously failed: {record.error}")

        if record.prompt_id is None:
            record.prompt_id = self.client.queue_workflow(workflow)
            record.status = "queued"
            self._write_json(job_file, asdict(record))
            logger.info("queued", extra={"job_id": job_id})

        try:
            history = self.client.wait_for_completion(record.prompt_id)
            outputs = self.client.download_outputs(history, job_dir / "output")
        except ComfyUIError as exc:
            if "Timed out" not in str(exc):
                record.status = "failed"
                record.error = str(exc)
                self._write_json(job_file, asdict(record))
            logger.exception("job execution failed", extra={"job_id": job_id})
            raise

        record.outputs = [str(path.resolve()) for path in outputs]
        record.status = "completed"
        self._write_json(job_file, asdict(record))
        logger.info("completed", extra={"job_id": job_id})
        return record

    def resume(self, job_id: str) -> JobRecord:
        if not job_id or any(char not in "0123456789abcdef" for char in job_id):
            raise ValueError("Invalid job_id")
        workflow_file = self.jobs_dir / job_id / "workflow.json"
        if not workflow_file.exists():
            raise FileNotFoundError(workflow_file)
        workflow = json.loads(workflow_file.read_text(encoding="utf-8"))
        if self.identity(workflow) != job_id:
            raise ValueError("Job ID does not match stored workflow")
        return self.run(workflow)
