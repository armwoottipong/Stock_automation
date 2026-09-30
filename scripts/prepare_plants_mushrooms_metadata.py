"""Prepare Adobe Stock metadata catalog for 500 plants and mushrooms."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_image_automation.stock_metadata import export_csv, validate_catalog

SET_ID = "plants_mushrooms_500_2026-09-30_001"
STAGING_DIR = ROOT / "staging" / SET_ID


def build_catalog() -> dict:
    batch_plan = json.loads((ROOT / "jobs" / "batches" / "c9273d01fed70f71" / "batch_plan.json").read_text(encoding="utf-8"))
    records = []
    base_kws = ["isolated", "cutout", "transparent background", "nature", "botanical"]

    for item in batch_plan["items"]:
        item_id = item["id"]
        parts = item_id.rsplit("_", 1)
        raw_name = parts[0]
        var_num = int(parts[1])
        title_name = raw_name.replace("_", " ").title()

        is_mushroom = any(k in raw_name for k in [
            "shiitake", "portobello", "cremini", "button", "oyster", "chanterelle", "morel", "porcini",
            "enoki", "maitake", "shimeji", "lion_mane", "reishi", "cordyceps", "turkey_tail", "chaga",
            "matsutake", "trumpet", "agaric", "death_cap", "honey_fungus", "parasol", "puffball", "blewit",
            "inky_cap", "lobster", "ear", "snow_fungus", "cauliflower", "hedgehog", "milk_cap", "bolete",
            "scarlet_cup", "deceiver", "glow_mushroom"
        ])

        if is_mushroom:
            title_templates = {
                1: f"Fresh {title_name} Centered Whole Specimen Isolate",
                2: f"Single {title_name} Top Down View Specimen",
                3: f"Side Profile View of Fresh {title_name}",
                4: f"Natural Cluster of Fresh {title_name} Specimens",
                5: f"Young Fresh {title_name} Button Specimen Isolate",
            }
            extra_kws = ["mushroom", "fungus", "edible", "culinary", "ingredient", "organic", "raw food", "produce"]
            category = "12"
        else:
            title_templates = {
                1: f"Fresh Healthy {title_name} Centered Full View",
                2: f"Single {title_name} Top Down View Foliage",
                3: f"Side Profile View of Fresh {title_name}",
                4: f"Detailed View of Natural {title_name} Texture",
                5: f"Young Fresh {title_name} New Growth Botanical",
            }
            extra_kws = ["plant", "greenery", "foliage", "leaf", "indoor plant", "garden", "herbal"]
            category = "12"

        raw_title = title_templates.get(var_num, f"Fresh {title_name} Botanical Isolate")
        clean_title = re.sub(r"[^\w\s-]", "", raw_title)

        kws = [
            raw_name.replace("_", " "),
            title_name.lower(),
            *extra_kws,
            *base_kws,
        ]
        kws = list(dict.fromkeys(kws))

        records.append({
            "filename": f"{item_id}.png",
            "title": clean_title,
            "keywords": kws,
            "adobe_category": category,
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
