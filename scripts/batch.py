"""Plan, run, resume and inspect a frozen batch of image jobs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_image_automation.batch import (  # noqa: E402
    BatchManifest, batch_report, build_batch_plan, freeze_batch, load_batch, run_batch,
)
from ai_image_automation.research_cache import load_context  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Frozen, resumable image batch")
    actions = parser.add_subparsers(dest="action", required=True)
    plan_action = actions.add_parser("plan", help="Validate and freeze the complete batch")
    plan_action.add_argument("--manifest", type=Path, required=True)
    plan_action.add_argument("--batches-dir", type=Path, default=ROOT / "jobs" / "batches")
    run_action = actions.add_parser("run", help="Run or resume a frozen batch")
    run_action.add_argument("--plan", type=Path, required=True)
    run_action.add_argument("--retry-failed", action="store_true", help="Start another bounded attempt round for failed items")
    status_action = actions.add_parser("status", help="Read file-level progress and report")
    status_action.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "plan":
            manifest = BatchManifest.model_validate_json(args.manifest.read_text(encoding="utf-8"))
            plan = build_batch_plan(manifest, load_context(ROOT / "data"))
            path = freeze_batch(plan, args.batches_dir)
            result = {"batch_id": plan["batch_id"], "total": len(plan["items"]), "plan": str(path.resolve())}
        elif args.action == "status":
            path = args.plan.resolve()
            result = batch_report(load_batch(path), path.parent)
        else:
            def show_progress(report: dict) -> None:
                print(json.dumps({
                    "batch_id": report["batch_id"], "finished": report["finished"],
                    "total": report["total"], "progress_percent": report["progress_percent"],
                    "running": report["counts"]["running"],
                    "pending_retry": report["counts"]["pending_retry"],
                }), flush=True)

            result = run_batch(
                args.plan.resolve(), root=ROOT, on_progress=show_progress,
                retry_failed=args.retry_failed,
            )
    except Exception as exc:
        print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 2 if args.action == "run" and result["counts"]["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
