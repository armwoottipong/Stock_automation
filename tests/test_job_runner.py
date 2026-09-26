import json

import pytest

from ai_image_automation.comfyui.client import ComfyUIError
from ai_image_automation.jobs.runner import JobRunner


class FakeClient:
    def __init__(self):
        self.queued = 0
        self.fail_wait = False

    def queue_workflow(self, workflow):
        self.queued += 1
        return "prompt-123"

    def wait_for_completion(self, prompt_id, **_kwargs):
        if self.fail_wait:
            raise ComfyUIError("Timed out")
        return {"outputs": {"1": {"images": [{"filename": "x.png", "type": "output"}]}}}

    def download_outputs(self, _history, output_dir):
        output_dir.mkdir(parents=True, exist_ok=True)
        target = output_dir / "image_001.png"
        target.write_bytes(b"image")
        return [target]


def test_job_resumes_without_duplicate_queue(tmp_path):
    client = FakeClient()
    runner = JobRunner(client, tmp_path)
    workflow = {"1": {"class_type": "SaveImage", "inputs": {}}}
    client.fail_wait = True
    with pytest.raises(ComfyUIError, match="Timed out"):
        runner.run(workflow)
    assert client.queued == 1
    client.fail_wait = False
    result = runner.run(workflow)
    assert client.queued == 1
    assert result.status == "completed"
    assert len(result.outputs) == 1
    stored = json.loads((tmp_path / result.job_id / "job.json").read_text(encoding="utf-8"))
    assert stored["prompt_id"] == "prompt-123"
    assert stored["status"] == "completed"
    assert runner.run(workflow).job_id == result.job_id
    assert client.queued == 1


def test_workflow_identity_is_order_independent(tmp_path):
    client = FakeClient()
    runner = JobRunner(client, tmp_path)
    left = {"2": {"inputs": {"a": 1}}, "1": {"inputs": {"b": 2}}}
    right = {"1": {"inputs": {"b": 2}}, "2": {"inputs": {"a": 1}}}
    assert runner.run(left).job_id == runner.run(right).job_id
    assert client.queued == 1


def test_completed_checkpoint_requires_real_output(tmp_path):
    client = FakeClient()
    runner = JobRunner(client, tmp_path)
    workflow = {"1": {"class_type": "SaveImage", "inputs": {}}}
    record = runner.run(workflow)
    job_file = tmp_path / record.job_id / "job.json"
    stored = json.loads(job_file.read_text(encoding="utf-8"))
    stored["outputs"] = []
    job_file.write_text(json.dumps(stored), encoding="utf-8")
    with pytest.raises(ComfyUIError, match="missing output"):
        runner.run(workflow)


def test_failed_job_does_not_persist_server_details(tmp_path):
    class FailingClient(FakeClient):
        def wait_for_completion(self, prompt_id, **kwargs):
            raise ComfyUIError("server returned secret-token and prompt text")

    runner = JobRunner(FailingClient(), tmp_path)
    workflow = {"1": {"class_type": "SaveImage", "inputs": {}}}
    with pytest.raises(ComfyUIError):
        runner.run(workflow)
    job_dir = tmp_path / runner.identity(workflow)
    assert "secret-token" not in (job_dir / "job.json").read_text(encoding="utf-8")
    assert "secret-token" not in (job_dir / "logs" / "runtime.jsonl").read_text(encoding="utf-8")
