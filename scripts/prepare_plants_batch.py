"""Prepare 250 plants & flowers batch manifest for 50 new species x 5 variations."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_image_automation.batch import BatchManifest, build_batch_plan, freeze_batch
from ai_image_automation.research_cache import load_context

# 40 previously done flowers to strictly forbid:
PREVIOUS_FLOWERS = {
    "rose", "sunflower", "tulip", "orchid", "daisy", "lily", "lotus", "hibiscus",
    "lavender", "peony", "hydrangea", "carnation", "marigold", "jasmine", "frangipani",
    "cherry_blossom", "dandelion", "gerbera", "iris", "daffodil", "poppy", "chrysanthemum",
    "dahlia", "camellia", "magnolia", "bird_of_paradise", "anemone", "freesia", "violet",
    "gardenia", "begonia", "morning_glory", "zinnia", "cosmos", "bougainvillea", "anthurium",
    "ranunculus", "amaryllis", "gladiolus", "water_lily"
}

# 50 completely new plant and flower species (25 indoor/succulent/foliage/herb plants + 25 distinct flowers)
SPECIES = [
    # Foliage & Indoor & Succulents & Herbs (25 species)
    ("monstera", "monstera deliciosa leaf with natural splits", "plant"),
    ("snake_plant", "sansevieria snake plant with tall striped green leaves", "plant"),
    ("fiddle_leaf_fig", "fiddle leaf fig plant with broad violin shaped leaves", "plant"),
    ("aloe_vera", "aloe vera succulent plant with thick fleshy green leaves", "plant"),
    ("pothos", "golden pothos vine with variegated heart shaped leaves", "plant"),
    ("calathea", "calathea peacock plant with patterned green leaves", "plant"),
    ("peace_lily", "peace lily plant with dark foliage and single white spathe", "flower"),
    ("zz_plant", "zamioculcas zamiifolia zz plant with glossy oval leaves", "plant"),
    ("rubber_plant", "burgundy rubber plant with thick shiny oval leaves", "plant"),
    ("boston_fern", "boston fern frond with lush green feathery leaflets", "plant"),
    ("spider_plant", "chlorophytum spider plant with arching variegated leaves", "plant"),
    ("echeveria", "echeveria rosette succulent with fleshy blue green leaves", "plant"),
    ("jade_plant", "crassula ovata jade plant with thick rounded green leaves", "plant"),
    ("string_of_pearls", "string of pearls succulent trailing vine with round bead leaves", "plant"),
    ("bamboo_palm", "chamaedorea bamboo palm frond with slender green leaflets", "plant"),
    ("eucalyptus", "silver dollar eucalyptus branch with round blue green leaves", "plant"),
    ("rosemary", "fresh rosemary herb sprig with slender aromatic green needles", "plant"),
    ("basil", "fresh green sweet basil sprig with fragrant tender leaves", "plant"),
    ("mint", "fresh spearmint sprig with textured green leaves", "plant"),
    ("thyme", "fresh green thyme herb sprig with tiny aromatic leaves", "plant"),
    ("cactus", "prickly pear desert cactus with round pads and small blossom", "plant"),
    ("birds_nest_fern", "asplenium birds nest fern with wavy glossy green fronds", "plant"),
    ("philodendron", "heartleaf philodendron with trailing green leaves", "plant"),
    ("croton", "codiaeum croton plant with vivid colorful yellow red green leaves", "plant"),
    ("agave", "blue agave desert succulent rosette with pointed spine leaves", "plant"),

    # Flowers (25 distinct species)
    ("hyacinth", "purple hyacinth flower cluster in full bloom", "flower"),
    ("snapdragon", "colorful snapdragon flower spike in open bloom", "flower"),
    ("foxglove", "digitalis purple foxglove flower spike with spotted bells", "flower"),
    ("petunia", "purple petunia flower bloom with velvety petals", "flower"),
    ("delphinium", "deep blue delphinium larkspur flower spike in blossom", "flower"),
    ("bleeding_heart", "pink bleeding heart flower vine with heart shaped blossoms", "flower"),
    ("aster", "purple aster flower bloom with fine ray petals and yellow disk", "flower"),
    ("calla_lily", "white calla lily trumpet bloom with yellow spadix", "flower"),
    ("columbine", "aquilegia two-tone columbine flower bloom with delicate spurs", "flower"),
    ("forget_me_not", "sky blue forget-me-not flower cluster with tiny yellow centers", "flower"),
    ("pansy", "tricolor purple and yellow pansy flower blossom", "flower"),
    ("bluebell", "english bluebell flower cluster with nodding violet blue bells", "flower"),
    ("dianthus", "pink dianthus carnation-relative flower with fringed petals", "flower"),
    ("clover", "fresh green four-leaf clover sprig with delicate leaves", "plant"),
    ("poinsettia", "red poinsettia holiday flower with vibrant star shaped bracts", "flower"),
    ("wisteria", "hanging purple wisteria flower cluster in full blossom", "flower"),
    ("snowdrop", "delicate white snowdrop galanthus flower nodding downward", "flower"),
    ("crocus", "purple spring crocus flower blossom opening upward", "flower"),
    ("sweet_pea", "fragrant pink sweet pea flower blossom with ruffled petals", "flower"),
    ("hollyhock", "tall pink hollyhock flower bloom with wide cup petals", "flower"),
    ("alstroemeria", "peruvian lily alstroemeria flower with speckled throat", "flower"),
    ("statice", "purple sea lavender statice flower cluster in bloom", "flower"),
    ("yucca", "yucca plant rosette with stiff sword shaped pointed leaves", "plant"),
    ("pilea", "pilea peperomioides chinese money plant with round coin leaves", "plant"),
    ("dieffenbachia", "dieffenbachia dumb cane leaf with mottled cream green pattern", "plant"),
]

PLANT_TEMPLATES = [
    "fresh healthy {name}, full view centered",
    "single {name} leaf viewed directly from top down",
    "side profile view of fresh {name}",
    "detailed view of {name} showing natural texture",
    "young fresh {name} with tender new growth",
]

FLOWER_TEMPLATES = [
    "fresh {name} in full open blossom",
    "single {name} viewed directly from top down",
    "side profile view of blooming {name}",
    "{name} with natural green stem and leaves",
    "fresh {name} bud gently opening into blossom",
]


def build_manifest() -> tuple[dict, Path]:
    # Check no overlap
    for sid, _, _ in SPECIES:
        if sid in PREVIOUS_FLOWERS:
            raise ValueError(f"Duplicate species with previous set: {sid}")

    if len(SPECIES) != 50:
        raise ValueError(f"Expected exactly 50 species, got {len(SPECIES)}")

    set_id = "plants_flowers_250_2026-09-29_001"
    staging_dir = ROOT / "staging" / set_id
    staging_dir.mkdir(parents=True, exist_ok=True)

    items = []
    base_seed = 30000
    counter = 0

    for sid, name, category in SPECIES:
        templates = FLOWER_TEMPLATES if category == "flower" else PLANT_TEMPLATES
        for var_idx, template in enumerate(templates, start=1):
            counter += 1
            item_id = f"{sid}_{var_idx:02d}"
            desc = template.format(name=name)
            seed = base_seed + counter
            items.append({
                "id": item_id,
                "request": {
                    "operation": "generate",
                    "subject_type": "isolated_object",
                    "description": desc,
                    "seed": seed,
                },
            })

    manifest_data = {
        "schema_version": 1,
        "max_attempts": 2,
        "items": items,
    }
    
    out_manifest = staging_dir / "generation_batch.json"
    out_manifest.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote batch manifest with {len(items)} items to {out_manifest}")
    return manifest_data, out_manifest


def main():
    manifest_data, out_manifest = build_manifest()
    # Validate and freeze
    batch_manifest = BatchManifest.model_validate(manifest_data)
    plan = build_batch_plan(batch_manifest, load_context(ROOT / "data"))
    plan_path = freeze_batch(plan, ROOT / "jobs" / "batches")
    print(f"Batch plan frozen: batch_id={plan['batch_id']}, path={plan_path}")


if __name__ == "__main__":
    main()
