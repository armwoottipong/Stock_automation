"""Export a reviewed catalog to a platform CSV; never infer provenance from pixels."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_image_automation.stock_metadata import MetadataError, export_csv, load_catalog  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--platform", choices=("adobe", "shutterstock"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        csv_text = export_csv(load_catalog(args.catalog), args.platform, args.assets)
    except MetadataError as exc:
        parser.exit(2, f"Metadata export blocked: {exc}\n")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(csv_text, encoding="utf-8", newline="")
    print(f"Wrote {args.platform} metadata to {args.output}")


if __name__ == "__main__":
    main()
