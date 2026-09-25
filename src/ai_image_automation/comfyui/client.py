"""Small synchronous client for ComfyUI's local HTTP API."""

import json
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ComfyUIError(RuntimeError):
    """A ComfyUI connection, protocol, or execution failure."""


class ComfyUIClient:
    def __init__(self, base_url: str, *, timeout_seconds: float = 30):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _request(self, path: str, payload: dict[str, Any] | None = None) -> bytes:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json"} if body is not None else {},
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise ComfyUIError(f"ComfyUI HTTP {exc.code}: {detail}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise ComfyUIError(f"Cannot connect to ComfyUI at {self.base_url}: {exc}") from exc

    def _json(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            value = json.loads(self._request(path, payload))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ComfyUIError(f"Invalid JSON from ComfyUI {path}") from exc
        if not isinstance(value, dict):
            raise ComfyUIError(f"Expected JSON object from ComfyUI {path}")
        return value

    def health(self) -> dict[str, Any]:
        return self._json("/system_stats")

    def queue_workflow(self, workflow: dict[str, Any]) -> str:
        result = self._json("/prompt", {"prompt": workflow})
        prompt_id = result.get("prompt_id")
        if not isinstance(prompt_id, str) or not prompt_id:
            raise ComfyUIError(f"ComfyUI did not return prompt_id: {result}")
        return prompt_id

    def history(self, prompt_id: str) -> dict[str, Any]:
        return self._json(f"/history/{prompt_id}")

    def wait_for_completion(
        self, prompt_id: str, *, timeout_seconds: float = 3600, poll_seconds: float = 2
    ) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            job = self.history(prompt_id).get(prompt_id)
            if isinstance(job, dict):
                status = job.get("status", {})
                if status.get("status_str") == "error":
                    raise ComfyUIError(f"ComfyUI job {prompt_id} failed: {status}")
                if status.get("completed"):
                    return job
            time.sleep(poll_seconds)
        raise ComfyUIError(f"Timed out waiting for ComfyUI job {prompt_id}")

    def download_outputs(self, history: dict[str, Any], output_dir: Path) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        saved: list[Path] = []
        for node in history.get("outputs", {}).values():
            for item in node.get("images", []):
                if item.get("type") != "output":
                    continue
                query = urlencode({
                    "filename": item["filename"],
                    "subfolder": item.get("subfolder", ""),
                    "type": "output",
                })
                suffix = Path(item["filename"]).suffix.lower()
                if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
                    raise ComfyUIError(f"Unsupported output extension: {suffix}")
                target = output_dir / f"image_{len(saved) + 1:03d}{suffix}"
                target.write_bytes(self._request(f"/view?{query}"))
                saved.append(target)
        if not saved:
            raise ComfyUIError("ComfyUI completed without image outputs")
        return saved
