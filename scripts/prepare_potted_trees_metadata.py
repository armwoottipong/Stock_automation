"""Prepare Adobe Stock metadata catalog for 500 potted trees."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_image_automation.stock_metadata import export_csv, validate_catalog

BATCH_ID = "6b2e5fc9a1046a6d"
SET_ID = "potted_trees_500_2026-10-01_001"
STAGING_DIR = ROOT / "staging" / SET_ID


def build_catalog() -> dict:
    batch_plan = json.loads((ROOT / "jobs" / "batches" / BATCH_ID / "batch_plan.json").read_text(encoding="utf-8"))
    records = []
    base_kws = [
        "potted tree", "houseplant", "indoor plant", "tree in pot",
        "botanical", "isolated", "cutout", "greenery", "foliage",
        "interior decor", "gardening", "flowerpot", "planter",
        "nature", "flora", "transparent background"
    ]

    title_templates = {
        1: "Potted {name} Tree in White Ceramic Pot",
        2: "Elegant Potted {name} Tree in Terracotta Planter",
        3: "Modern Architectural {name} Tree in Grey Pot",
        4: "Lush Potted {name} Tree in Stoneware Pot",
        5: "Tall Slender Potted {name} Indoor Tree Specimen",
        6: "Young Potted {name} Sapling Tree in Ceramic Planter",
        7: "Sculptural Potted {name} Tree Bonsai Style",
        8: "Decorative Potted {name} Tree in Charcoal Pot",
        9: "Graceful Potted {name} Indoor Tree with Planter",
        10: "Minimalist Potted {name} Houseplant Tree in Stone Pot",
    }

    for item in batch_plan["items"]:
        item_id = item["id"]
        parts = item_id.rsplit("_", 1)
        raw_name = parts[0]
        var_num = int(parts[1])
        title_name = raw_name.replace("_", " ").title()

        extra_kws = []
        if "ficus" in raw_name:
            extra_kws.extend(["fig tree", "ficus plant", "tropical tree"])
        if "bonsai" in raw_name or var_num == 7:
            extra_kws.extend(["bonsai tree", "japanese bonsai", "dwarf tree", "sculpted tree"])
        if "palm" in raw_name:
            extra_kws.extend(["palm tree", "tropical palm", "fronds"])
        if "pine" in raw_name or "juniperus" in raw_name:
            extra_kws.extend(["conifer", "evergreen", "pine needles"])
        if "citrus" in raw_name or "lemon" in raw_name or "orange" in raw_name:
            extra_kws.extend(["fruit tree", "citrus tree"])
        if "jade" in raw_name or "crassula" in raw_name or "adenium" in raw_name or "cactus" in raw_name:
            extra_kws.extend(["succulent tree", "succulent plant", "thick trunk"])

        raw_title = title_templates.get(var_num, "Potted {name} Indoor Tree Botanical Isolate").format(name=title_name)
        clean_title = re.sub(r"[^\w\s-]", "", raw_title)

        kws = [
            raw_name.replace("_", " "),
            title_name.lower(),
            *extra_kws,
            *base_kws,
        ]
        # De-duplicate while preserving order
        kws = list(dict.fromkeys(kws))

        records.append({
            "filename": f"{item_id}.png",
            "title": clean_title,
            "keywords": kws,
            "adobe_category": "12",
        })

    catalog = {
        "language": "en",
        "source_type": "generative_ai",
        "records": records,
    }
    return catalog


def main():
    catalog = build_catalog()
    cat_file = STAGING_DIR / "catalog.json"
    cat_file.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    csv_text = export_csv(catalog, "adobe")
    (STAGING_DIR / "adobe_stock.csv").write_text(csv_text, encoding="utf-8")
    print(f"Metadata catalog and CSV generated for {len(catalog['records'])} items.")


if __name__ == "__main__":
    main()
