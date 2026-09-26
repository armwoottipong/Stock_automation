"""Prepare review-only stock metadata for the 2026-09-26 fruit set."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_image_automation.stock_metadata import MetadataError, export_csv  # noqa: E402


DETAILS = {
    "apple_01_whole_red": ("Whole red apple isolated on transparent background", ["red apple", "whole", "single"]),
    "apple_02_halved_red": ("Whole and halved red apple isolated on transparent background", ["red apple", "halved", "whole", "cut fruit"]),
    "apple_03_green_single": ("Whole green apple with leaf isolated on transparent background", ["green apple", "whole", "single", "leaf"]),
    "apple_04_red_slices": ("Red apple wedges isolated on transparent background", ["red apple", "wedges", "sliced fruit"]),
    "apple_05_two_colors": ("Red and green apples isolated on transparent background", ["red apple", "green apple", "pair", "whole"]),
    "banana_01_whole": ("Whole yellow banana isolated on transparent background", ["yellow banana", "whole", "single"]),
    "banana_02_peeled": ("Partly peeled banana isolated on transparent background", ["peeled banana", "banana peel", "whole"]),
    "banana_03_bunch": ("Bunch of three bananas isolated on transparent background", ["banana bunch", "three bananas", "whole"]),
    "banana_04_slices": ("Round banana slices isolated on transparent background", ["banana slices", "round slices", "cut fruit"]),
    "banana_05_halved_lengthwise": ("Two lengthwise banana halves isolated on transparent background", ["banana halves", "halved", "cut fruit"]),
    "lemon_01_whole": ("Whole yellow lemon isolated on transparent background", ["yellow lemon", "whole", "single"]),
    "lemon_02_half": ("Whole and halved lemon isolated on transparent background", ["yellow lemon", "halved", "whole", "cut fruit"]),
    "lemon_03_slices": ("Round lemon slices isolated on transparent background", ["lemon slices", "round slices", "cut fruit"]),
    "lemon_04_wedges": ("Yellow lemon wedges isolated on transparent background", ["lemon wedges", "cut fruit", "yellow"]),
    "lemon_05_twist": ("Whole lemon with peel curl isolated on transparent background", ["yellow lemon", "lemon peel", "peel curl", "whole"]),
    "orange_01_whole": ("Whole orange fruit isolated on transparent background", ["orange fruit", "whole", "single"]),
    "orange_02_half": ("Whole and halved orange isolated on transparent background", ["orange fruit", "halved", "whole", "cut fruit"]),
    "orange_03_slices": ("Round orange slices isolated on transparent background", ["orange slices", "round slices", "cut fruit"]),
    "orange_04_peeled": ("Partly peeled orange isolated on transparent background", ["orange fruit", "orange peel", "peeled"]),
    "orange_05_wedges": ("Orange fruit wedges isolated on transparent background", ["orange wedges", "cut fruit", "citrus"]),
    "strawberry_01_single": ("Single whole strawberry isolated on transparent background", ["red strawberry", "whole", "single"]),
    "strawberry_02_half": ("Whole and halved strawberries isolated on transparent background", ["red strawberry", "halved", "whole", "cut fruit"]),
    "strawberry_03_pair": ("Pair of strawberries isolated on transparent background", ["red strawberry", "pair", "whole"]),
    "strawberry_04_slices": ("Sliced strawberries isolated on transparent background", ["strawberry slices", "sliced fruit", "red"]),
    "strawberry_05_trio": ("Three whole strawberries isolated on transparent background", ["red strawberry", "three strawberries", "whole"]),
}


def build_catalog(manifest: dict, *, cutout_key: str = "cutout") -> dict:
    records = []
    for item in manifest["records"]:
        name = item["name"]
        title, detail = DETAILS[name]
        fruit = name.split("_")[0]
        keywords = [fruit, *detail, "fruit", "isolated", "transparent background", "cutout", "food", "produce"]
        keywords = list(dict.fromkeys(keywords))
        records.append({
            "filename": Path(item[cutout_key]).name,
            "title": title,
            "keywords": keywords,
            "shutterstock_category": "Food and drink",
            "stock_review_required": True,
        })
    if len(records) != 25 or len(DETAILS) != 25:
        raise MetadataError("Expected exactly 25 fruit records")
    return {
        "source_type": "generative_ai",
        "language": "en",
        "review_status": "draft_manual_review_required",
        "adobe_portal_action": "Select Created using generative AI tools before submission",
        "shutterstock_eligible": False,
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("output/fruit_isolates_2026-09-26"))
    parser.add_argument("--manifest", default="manifest.json")
    parser.add_argument("--metadata-dir", default="metadata")
    parser.add_argument("--assets", default="cutout")
    args = parser.parse_args()
    root = args.root
    manifest = json.loads((root / args.manifest).read_text(encoding="utf-8"))
    catalog = build_catalog(manifest, cutout_key=args.assets)
    catalog["scale_from_original"] = manifest.get("scale_from_original", 2)
    csv_text = export_csv(catalog, "adobe", root / args.assets)
    folder = root / args.metadata_dir
    folder.mkdir(exist_ok=True)
    (folder / "catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (folder / "adobe_stock_draft.csv").write_text(csv_text, encoding="utf-8", newline="")
    print(f"Wrote {len(catalog['records'])} Adobe metadata rows; Shutterstock blocked by source_type")


if __name__ == "__main__":
    main()
