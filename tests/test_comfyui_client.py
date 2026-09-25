import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from ai_image_automation.comfyui.client import ComfyUIClient, ComfyUIError
from ai_image_automation.cli import main


@pytest.fixture
def fake_comfyui():
    calls = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            calls.append(("GET", self.path))
            if self.path == "/system_stats":
                body = {"devices": [{"type": "cuda", "vram_total": 8_000_000_000}]}
            elif self.path == "/history/abc":
                body = {"abc": {"status": {"completed": True, "status_str": "success"}, "outputs": {"1": {"images": [{"filename": "result.png", "subfolder": "", "type": "output"}]}}}}
            elif self.path.startswith("/view?"):
                data = b"PNG DATA"
                self.send_response(200)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            else:
                self.send_error(404)
                return
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            length = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(length))
            calls.append(("POST", self.path, body))
            data = json.dumps({"prompt_id": "abc"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}", calls
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def test_health_queue_wait_and_download(fake_comfyui, tmp_path):
    url, calls = fake_comfyui
    client = ComfyUIClient(url, timeout_seconds=2)
    assert client.health()["devices"][0]["type"] == "cuda"
    assert client.queue_workflow({"1": {"class_type": "SaveImage", "inputs": {}}}) == "abc"
    history = client.wait_for_completion("abc", timeout_seconds=2, poll_seconds=0.01)
    paths = client.download_outputs(history, tmp_path)
    assert len(paths) == 1
    assert paths[0].read_bytes() == b"PNG DATA"
    assert calls[1][2]["prompt"]["1"]["class_type"] == "SaveImage"


def test_health_reports_connection_failure():
    client = ComfyUIClient("http://127.0.0.1:1", timeout_seconds=0.2)
    with pytest.raises(ComfyUIError, match="connect"):
        client.health()


def test_cli_health_reports_device(fake_comfyui, capsys):
    url, _calls = fake_comfyui
    assert main(["--url", url, "health"]) == 0
    assert '"type": "cuda"' in capsys.readouterr().out


def test_cli_submit_and_resume(fake_comfyui, tmp_path, capsys):
    url, calls = fake_comfyui
    workflow_file = tmp_path / "workflow.json"
    workflow_file.write_text(json.dumps({"1": {"class_type": "SaveImage", "inputs": {}}}), encoding="utf-8")
    jobs_dir = tmp_path / "jobs"
    assert main(["--url", url, "--jobs-dir", str(jobs_dir), "submit", "--workflow", str(workflow_file)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "completed"
    assert main(["--url", url, "--jobs-dir", str(jobs_dir), "resume", result["job_id"]]) == 0
    assert sum(1 for call in calls if call[:2] == ("POST", "/prompt")) == 1
