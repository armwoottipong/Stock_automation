import json
import io
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from PIL import Image

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
                image = Image.new("RGB", (64, 64), "white")
                image.putpixel((0, 0), (0, 0, 0))
                stream = io.BytesIO()
                image.save(stream, format="PNG")
                data = stream.getvalue()
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
    with Image.open(paths[0]) as image:
        assert image.size == (64, 64)
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


def test_cli_generate_builds_workflow_and_runs_qc(fake_comfyui, tmp_path, capsys):
    url, calls = fake_comfyui
    checkpoint = tmp_path / "sdxl.safetensors"
    checkpoint.write_bytes(b"test")
    registry = tmp_path / "models.json"
    registry.write_text(json.dumps({"schema_version": 1, "records": [{
        "id": "sdxl-base-1.0", "name": "SDXL Base", "tasks": ["generate"],
        "commercial_use": "allowed", "license": "OpenRAIL++", "source": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0",
        "last_verified": "2026-09-25", "installed": True, "local_path": str(checkpoint)
    }]}), encoding="utf-8")
    license_registry = tmp_path / "licenses.json"
    license_registry.write_text(json.dumps({"schema_version": 1, "records": [{
        "resource_id": "sdxl-base-1.0", "license": "OpenRAIL++", "commercial_use": "allowed",
        "source": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0",
        "last_verified": "2026-09-25"
    }]}), encoding="utf-8")
    assert main(["--url", url, "--jobs-dir", str(tmp_path / "jobs"), "generate",
                 "--prompt", "glass perfume", "--model-id", "sdxl-base-1.0",
                 "--registry", str(registry), "--license-registry", str(license_registry),
                 "--checkpoints-dir", str(tmp_path),
                 "--width", "64", "--height", "64"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "completed"
    assert calls[0][2]["prompt"]["2"]["inputs"]["text"] == "glass perfume"
    assert (tmp_path / "jobs" / result["job_id"] / "qc.json").is_file()


def test_cli_upscale_stages_input_and_runs_pixel_workflow(fake_comfyui, tmp_path, capsys):
    url, calls = fake_comfyui
    source = tmp_path / "source.png"
    Image.new("RGB", (32, 32), "red").save(source)
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    model = models_dir / "RealESRGAN_x2plus.pth"
    model.write_bytes(b"test")
    registry = tmp_path / "upscalers.json"
    registry.write_text(json.dumps({"schema_version": 1, "records": [{
        "id": "realesrgan-x2plus", "name": "RealESRGAN x2plus", "tasks": ["upscale"],
        "commercial_use": "allowed", "license": "BSD-3-Clause",
        "source": "https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.1",
        "last_verified": "2026-09-25", "installed": True, "local_path": str(model)
    }]}), encoding="utf-8")
    licenses = tmp_path / "licenses.json"
    licenses.write_text(json.dumps({"schema_version": 1, "records": [{
        "resource_id": "realesrgan-x2plus", "license": "BSD-3-Clause",
        "commercial_use": "allowed",
        "source": "https://github.com/xinntao/Real-ESRGAN/blob/master/LICENSE",
        "last_verified": "2026-09-25"
    }]}), encoding="utf-8")
    args = ["--url", url, "--jobs-dir", str(tmp_path / "jobs"), "upscale",
            "--input", str(source), "--registry", str(registry),
            "--license-registry", str(licenses), "--models-dir", str(models_dir),
            "--comfy-input-dir", str(tmp_path / "comfy-input")]
    assert main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "completed"
    queued = next(call[2]["prompt"] for call in calls if call[:2] == ("POST", "/prompt"))
    assert queued["2"]["inputs"]["model_name"] == model.name
    assert (tmp_path / "comfy-input" / queued["1"]["inputs"]["image"]).is_file()
    assert (tmp_path / "jobs" / result["job_id"] / "qc.json").is_file()


def test_cli_creative_upscale_uses_guided_control_image(fake_comfyui, tmp_path, capsys):
    url, calls = fake_comfyui
    source = tmp_path / "source.png"
    Image.new("RGB", (64, 64), "red").save(source)
    checkpoints_dir = tmp_path / "checkpoints"
    controlnets_dir = tmp_path / "controlnets"
    checkpoints_dir.mkdir()
    controlnets_dir.mkdir()
    checkpoint = checkpoints_dir / "sdxl.safetensors"
    controlnet = controlnets_dir / "tile.safetensors"
    checkpoint.write_bytes(b"test")
    controlnet.write_bytes(b"test")
    def registry_file(path, record):
        path.write_text(json.dumps({"schema_version": 1, "records": [record]}), encoding="utf-8")
        return path
    checkpoint_registry = registry_file(tmp_path / "models.json", {
        "id": "sdxl", "name": "SDXL", "tasks": ["generate"],
        "commercial_use": "allowed", "license": "OpenRAIL++", "source": "https://example.com/sdxl",
        "last_verified": "2026-09-25", "installed": True, "local_path": str(checkpoint),
    })
    controlnet_registry = registry_file(tmp_path / "controlnets.json", {
        "id": "tile", "name": "Tile", "tasks": ["creative_upscale"],
        "commercial_use": "allowed", "license": "Apache-2.0", "source": "https://example.com/tile",
        "last_verified": "2026-09-25", "installed": True, "local_path": str(controlnet),
    })
    licenses = tmp_path / "licenses.json"
    licenses.write_text(json.dumps({"schema_version": 1, "records": [
        {"resource_id": "sdxl", "license": "OpenRAIL++", "commercial_use": "allowed",
         "source": "https://example.com/sdxl", "last_verified": "2026-09-25"},
        {"resource_id": "tile", "license": "Apache-2.0", "commercial_use": "allowed",
         "source": "https://example.com/tile", "last_verified": "2026-09-25"},
    ]}), encoding="utf-8")
    assert main(["--url", url, "--jobs-dir", str(tmp_path / "jobs"), "creative-upscale",
                 "--input", str(source), "--prompt", "glass reflection", "--checkpoint-id", "sdxl",
                 "--controlnet-id", "tile", "--checkpoint-registry", str(checkpoint_registry),
                 "--controlnet-registry", str(controlnet_registry), "--license-registry", str(licenses),
                 "--checkpoints-dir", str(checkpoints_dir), "--controlnets-dir", str(controlnets_dir),
                 "--comfy-input-dir", str(tmp_path / "comfy-input")]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "completed"
    queued = next(call[2]["prompt"] for call in calls if call[:2] == ("POST", "/prompt"))
    assert queued["8"]["class_type"] == "UltimateSDUpscaleNoUpscale"
    assert (tmp_path / "comfy-input" / queued["2"]["inputs"]["image"]).is_file()
    assert (tmp_path / "jobs" / result["job_id"] / "qc.json").is_file()
