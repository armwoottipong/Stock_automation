"""Inspect or update reviewed local model research; never fetches network sources."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_image_automation.research_cache import load_context, lookup, upsert  # noqa: E402
from ai_image_automation.registry import ResearchEntry  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline reviewed research cache")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    actions = parser.add_subparsers(dest="action", required=True)
    find = actions.add_parser("lookup", help="Read a cached decision and its freshness")
    find.add_argument("--task", required=True)
    find.add_argument("--subject", required=True)
    refresh = actions.add_parser("upsert", help="Store a manually reviewed JSON entry")
    refresh.add_argument("--entry", type=Path, required=True)
    actions.add_parser("list", help="List cached decisions and freshness")
    args = parser.parse_args(argv)
    try:
        if args.action == "upsert":
            entry = ResearchEntry.model_validate_json(args.entry.read_text(encoding="utf-8"))
            result = {"entries": len(upsert(args.data_dir, entry).entries), "updated": [entry.task, entry.subject_type]}
        else:
            context = load_context(args.data_dir)
            if args.action == "lookup":
                result = lookup(context, args.task, args.subject).as_dict()
            else:
                result = [lookup(context, item.task, item.subject_type).as_dict() for item in context.cache.entries]
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
