"""Plan a stock image job, then execute only the frozen plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_image_automation.research_cache import load_context  # noqa: E402
from ai_image_automation.router import build_plan, freeze_plan, parse_intent, run_plan  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline plan and frozen execution router")
    actions = parser.add_subparsers(dest="action", required=True)
    plan_action = actions.add_parser("plan", help="Create an immutable plan from a structured request")
    plan_action.add_argument("--request", type=Path, required=True)
    plan_action.add_argument("--jobs-dir", type=Path, default=ROOT / "jobs")
    run_action = actions.add_parser("run", help="Execute a previously frozen plan")
    run_action.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == "plan":
            intent = parse_intent(json.loads(args.request.read_text(encoding="utf-8")))
            plan = build_plan(intent, load_context(ROOT / "data"))
            path = freeze_plan(plan, args.jobs_dir)
            result = {"plan_id": plan["plan_id"], "route": plan["route"], "workflow": plan["workflow"], "plan": str(path.resolve())}
        else:
            result = run_plan(args.plan.resolve(), root=ROOT)
    except Exception as exc:
        print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
