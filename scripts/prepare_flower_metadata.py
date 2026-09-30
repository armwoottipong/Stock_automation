"""Prepare Adobe Stock metadata catalog for the 200 flower isolates."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_image_automation.stock_metadata import export_csv, validate_catalog

STAGING = ROOT / "staging" / "flowers_200_2026-09-29"
MANIFEST_PATH = STAGING / "flowers_manifest.json"

FLOWER_NAMES = {
    "rose": ("Red Rose", ["rose", "red rose", "flower", "bloom", "petal", "romantic", "valentines", "floral"]),
    "sunflower": ("Yellow Sunflower", ["sunflower", "yellow sunflower", "flower", "bloom", "seed", "summer", "floral"]),
    "tulip": ("Pink Tulip", ["tulip", "pink tulip", "spring flower", "bloom", "petal", "garden", "floral"]),
    "orchid": ("Purple Orchid", ["orchid", "purple orchid", "exotic flower", "phalaenopsis", "bloom", "floral", "tropical"]),
    "daisy": ("White Daisy", ["daisy", "white daisy", "field flower", "bloom", "yellow center", "summer", "floral"]),
    "lily": ("White Lily", ["lily", "white lily", "bloom", "petal", "elegance", "wedding", "floral"]),
    "lotus": ("Pink Lotus", ["lotus", "sacred lotus", "water bloom", "petal", "spiritual", "peaceful", "floral"]),
    "hibiscus": ("Red Hibiscus", ["hibiscus", "red hibiscus", "tropical flower", "bloom", "hawaiian", "exotic", "floral"]),
    "lavender": ("Purple Lavender", ["lavender", "purple lavender", "herb", "sprig", "aromatic", "botanical", "floral"]),
    "peony": ("Pink Peony", ["peony", "pink peony", "lush bloom", "petal", "romantic", "spring", "floral"]),
    "hydrangea": ("Blue Hydrangea", ["hydrangea", "blue hydrangea", "flower cluster", "bloom", "garden", "summer", "floral"]),
    "carnation": ("Red Carnation", ["carnation", "red carnation", "ruffled bloom", "petal", "mothers day", "floral"]),
    "marigold": ("Orange Marigold", ["marigold", "orange marigold", "bloom", "petal", "autumn", "festival", "floral"]),
    "jasmine": ("White Jasmine", ["jasmine", "white jasmine", "sweet bloom", "fragrant", "petal", "aromatic", "floral"]),
    "frangipani": ("Plumeria Frangipani", ["plumeria", "frangipani", "tropical flower", "spa", "yellow center", "bloom", "floral"]),
    "cherry_blossom": ("Pink Cherry Blossom", ["cherry blossom", "sakura", "spring bloom", "delicate", "japan", "floral"]),
    "dandelion": ("Yellow Dandelion", ["dandelion", "yellow dandelion", "wildflower", "bloom", "meadow", "sunny", "floral"]),
    "gerbera": ("Orange Gerbera", ["gerbera", "gerbera daisy", "orange flower", "bright bloom", "cheerful", "floral"]),
    "iris": ("Blue Iris", ["iris", "blue iris", "purple iris", "spring bloom", "elegance", "perennial", "floral"]),
    "daffodil": ("Yellow Daffodil", ["daffodil", "yellow daffodil", "narcissus", "spring bloom", "trumpet", "floral"]),
    "poppy": ("Red Poppy", ["poppy", "red poppy", "wildflower", "remembrance", "bloom", "field", "floral"]),
    "chrysanthemum": ("Yellow Chrysanthemum", ["chrysanthemum", "yellow bloom", "autumn flower", "mums", "golden", "floral"]),
    "dahlia": ("Magenta Dahlia", ["dahlia", "magenta dahlia", "layered petals", "geometric", "bloom", "floral"]),
    "camellia": ("Pink Camellia", ["camellia", "pink camellia", "rose-like bloom", "winter flower", "delicate", "floral"]),
    "magnolia": ("White Magnolia", ["magnolia", "white magnolia", "large bloom", "tree flower", "spring", "floral"]),
    "bird_of_paradise": ("Bird Of Paradise", ["bird of paradise", "strelitzia", "crane flower", "tropical", "exotic", "floral"]),
    "anemone": ("White Anemone", ["anemone", "white anemone", "windflower", "dark center", "petal", "bloom", "floral"]),
    "freesia": ("Yellow Freesia", ["freesia", "yellow freesia", "spring bloom", "fragrant", "bell shaped", "floral"]),
    "violet": ("Purple Violet", ["violet", "purple violet", "wildflower", "woodland bloom", "sweet violet", "floral"]),
    "gardenia": ("White Gardenia", ["gardenia", "white gardenia", "fragrant flower", "waxy petal", "perfume", "floral"]),
    "begonia": ("Red Begonia", ["begonia", "red begonia", "shade flower", "potted plant", "bloom", "floral"]),
    "morning_glory": ("Blue Morning Glory", ["morning glory", "blue flower", "trumpet vine", "climbing flower", "bloom", "floral"]),
    "zinnia": ("Pink Zinnia", ["zinnia", "pink zinnia", "summer garden", "daisy-like", "bright bloom", "floral"]),
    "cosmos": ("Pink Cosmos", ["cosmos", "pink cosmos", "meadow flower", "wildflower", "delicate petal", "floral"]),
    "bougainvillea": ("Bougainvillea Cluster", ["bougainvillea", "magenta bracts", "paper flower", "tropical vine", "floral"]),
    "anthurium": ("Red Anthurium", ["anthurium", "flamingo flower", "red spathe", "tropical houseplant", "exotic", "floral"]),
    "ranunculus": ("Orange Ranunculus", ["ranunculus", "persian buttercup", "layered bloom", "spring", "orange flower", "floral"]),
    "amaryllis": ("Red Amaryllis", ["amaryllis", "hippeastrum", "large trumpet", "holiday flower", "bulb bloom", "floral"]),
    "gladiolus": ("Pink Gladiolus", ["gladiolus", "sword lily", "tall flower spike", "perennial bloom", "floral"]),
    "water_lily": ("White Water Lily", ["water lily", "nymphaea", "aquatic bloom", "pond flower", "floating petal", "floral"]),
}

VARIATION_TITLES = {
    1: "Fresh {name} in Full Blossom",
    2: "Single {name} Top Down View",
    3: "Blooming {name} Side Profile View",
    4: "Fresh {name} with Green Stem",
    5: "Opening Bud of Fresh {name}",
}

BASE_KEYWORDS = ["isolated", "cutout", "transparent background", "botanical", "nature", "plant"]


def build_catalog(manifest: dict) -> dict:
    records = []
    for item in manifest["records"]:
        item_id = item["id"]
        # extract flower key and var index
        parts = item_id.rsplit("_", 1)
        flower_key = parts[0]
        var_idx = int(parts[1])

        name, specific_kws = FLOWER_NAMES[flower_key]
        raw_title = VARIATION_TITLES[var_idx].format(name=name)
        # ensure clean title without special chars
        clean_title = re.sub(r"[^\w\s-]", "", raw_title)
        
        # combine keywords
        kws = [*specific_kws, *BASE_KEYWORDS]
        # deduplicate
        kws = list(dict.fromkeys(kws))

        records.append({
            "filename": f"{item_id}.png",
            "title": clean_title,
            "keywords": kws,
            "adobe_category": "12",  # Plants and Flowers
        })

    return {
        "language": "en",
        "source_type": "generative_ai",
        "records": records,
    }


def main():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    catalog = build_catalog(manifest)
    
    # validate
    out_dir = STAGING / "transparent_png"
    validate_catalog(catalog, "adobe", out_dir if out_dir.exists() else None)
    
    cat_path = STAGING / "catalog.json"
    cat_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    
    csv_text = export_csv(catalog, "adobe")
    csv_path = STAGING / "adobe_stock.csv"
    csv_path.write_text(csv_text, encoding="utf-8")
    
    print(f"Catalog and CSV successfully created for {len(catalog['records'])} flowers.")


if __name__ == "__main__":
    main()
