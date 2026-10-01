"""Prepare Adobe Stock metadata catalog for 500 potted home decor plants."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_image_automation.stock_metadata import export_csv, validate_catalog

BATCH_ID = "e5a027840ab4db64"
SET_ID = "potted_decor_plants_500_2026-10-01_001"
STAGING_DIR = ROOT / "staging" / SET_ID


def build_catalog() -> dict:
    batch_plan = json.loads((ROOT / "jobs" / "batches" / BATCH_ID / "batch_plan.json").read_text(encoding="utf-8"))
    records = []
    base_kws = [
        "potted plant", "houseplant", "indoor plant", "home decor",
        "room decor", "interior plant", "botanical", "isolated",
        "cutout", "greenery", "foliage", "interior design",
        "urban jungle", "flowerpot", "planter", "nature", "transparent background"
    ]

    title_templates = {
        1: "Potted {name} in White Ceramic Pot",
        2: "Lush Potted {name} in Terracotta Pot",
        3: "Modern Architectural {name} in Grey Pot",
        4: "Decorative Potted {name} in Stoneware Pot",
        5: "Artisanal Potted {name} in Ceramic Pot",
        6: "Vibrant Potted {name} in Fluted Planter",
        7: "Sleek Modern Potted {name} in Black Pot",
        8: "Aesthetic Potted {name} Living Room Decor",
        9: "Desktop Potted {name} in Ribbed Planter",
        10: "Earthy Potted {name} in Stone Pot",
    }

    for item in batch_plan["items"]:
        item_id = item["id"]
        parts = item_id.rsplit("_", 1)
        raw_name = parts[0]
        var_num = int(parts[1])
        title_name = raw_name.replace("_", " ").title()

        extra_kws = []
        if "monstera" in raw_name:
            extra_kws.extend(["monstera", "swiss cheese plant", "split leaves", "tropical foliage"])
        if "sansevieria" in raw_name:
            extra_kws.extend(["snake plant", "sansevieria", "air purifying", "succulent foliage"])
        if "zz_plant" in raw_name:
            extra_kws.extend(["zz plant", "zamioculcas", "glossy leaves", "resilient plant"])
        if any(k in raw_name for k in ["calathea", "maranta", "ctenanthe", "stromanthe"]):
            extra_kws.extend(["prayer plant", "calathea", "patterned leaves", "ornamental foliage"])
        if "philo" in raw_name:
            extra_kws.extend(["philodendron", "climbing vine", "tropical houseplant", "heartleaf"])
        if "pothos" in raw_name or "scindapsus" in raw_name:
            extra_kws.extend(["pothos", "epipremnum", "trailing vine", "marble queen", "indoor vine"])
        if "alocasia" in raw_name:
            extra_kws.extend(["alocasia", "elephant ear", "exotic plant", "sculptural foliage"])
        if "anthurium" in raw_name:
            extra_kws.extend(["anthurium", "flamingo flower", "heart foliage", "tropical bloom"])
        if "begonia" in raw_name:
            extra_kws.extend(["begonia", "angel wing", "polka dot plant", "ornamental begonia"])
        if "fern" in raw_name:
            extra_kws.extend(["fern", "fronds", "boston fern", "birds nest fern"])
        if any(k in raw_name for k in ["hoya", "pearls", "turtles", "peperomia"]):
            extra_kws.extend(["succulent", "trailing succulent", "hanging plant", "compact houseplant"])
        if "peace_lily" in raw_name:
            extra_kws.extend(["peace lily", "spathiphyllum", "white flower", "flowering houseplant"])
        if "pilea" in raw_name:
            extra_kws.extend(["pilea peperomioides", "chinese money plant", "scandinavian decor", "coin leaves"])

        raw_title = title_templates.get(var_num, "Potted {name} Indoor Houseplant Botanical").format(name=title_name)
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
