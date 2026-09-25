"""Phase 2 CLI for ComfyUI health and API workflow jobs."""

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from ai_image_automation.comfyui.client import ComfyUIClient, ComfyUIError
from ai_image_automation.config import ROOT, load_settings
from ai_image_automation.jobs.runner import JobRunner


def main(argv: Sequence[str] | None = None) -> int:
    settings = load_settings()
    parser = argparse.ArgumentParser(description="Local ComfyUI API controller")
    parser.add_argument("--url", default=settings.comfyui.base_url, help="ComfyUI base URL")
    parser.add_argument("--jobs-dir", type=Path, default=ROOT / "jobs")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("health", help="Check ComfyUI API and GPU")
    submit = commands.add_parser("submit", help="Submit an API-format workflow JSON")
    submit.add_argument("--workflow", type=Path, required=True)
    resume = commands.add_parser("resume", help="Resume a queued job")
    resume.add_argument("job_id")
    args = parser.parse_args(argv)

    client = ComfyUIClient(args.url, timeout_seconds=settings.comfyui.timeout_seconds)
    try:
        if args.command == "health":
            result = client.health()
        else:
            runner = JobRunner(client, args.jobs_dir)
            if args.command == "submit":
                workflow = json.loads(args.workflow.read_text(encoding="utf-8"))
                if not isinstance(workflow, dict):
                    raise ValueError("Workflow must be a JSON object")
                result = runner.run(workflow).__dict__
            else:
                result = runner.resume(args.job_id).__dict__
    except (ComfyUIError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
