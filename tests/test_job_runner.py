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
