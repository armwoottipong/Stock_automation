"""Preview disk use and optionally remove stale job temporary files."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_image_automation.maintenance import inspect_jobs  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect disk and stale job temporary files")
    parser.add_argument("--older-than-days", type=int, default=7)
    parser.add_argument("--apply", action="store_true", help="Delete listed stale temporary files")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(inspect_jobs(ROOT, older_than_days=args.older_than_days, apply=args.apply), indent=2))
    except (OSError, ValueError) as exc:
        print(f"Maintenance failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
