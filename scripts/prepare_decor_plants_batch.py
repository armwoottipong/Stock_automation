"""Prepare 500 items batch: 50 popular home decor potted plants x 10 variations."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_image_automation.batch import BatchManifest, build_batch_plan, freeze_batch
from ai_image_automation.research_cache import load_context

SET_ID = "potted_decor_plants_500_2026-10-01_001"
STAGING_DIR = ROOT / "staging" / SET_ID

# 50 popular home & room decor potted plants (All IDs <= 23 chars so filename <= 30 chars)
DECOR_PLANTS = [
    ("monstera_deliciosa", "monstera deliciosa swiss cheese plant with large glossy perforated split leaves"),
    ("monstera_albo", "variegated monstera albo borsigiana plant with pure white marbling on green split leaves"),
    ("monstera_dubia", "monstera dubia shingling climbing foliage plant on central cedar plank pole"),
    ("sansevieria_laurentii", "sansevieria trifasciata laurentii snake plant with yellow-edged sword upright leaves"),
    ("sansevieria_cylindrica", "sansevieria cylindrica african spear plant with smooth cylindrical architectural spears"),
    ("sansevieria_whale_fin", "sansevieria masoniana whale fin plant with single giant mottled paddle leaf"),
    ("zz_plant_green", "zamioculcas zamiifolia emerald zz plant with upright stems of glossy dark green leaflets"),
    ("zz_plant_raven", "zamioculcas zamiifolia raven black zz plant with dramatic dark purple-black glossy leaves"),
    ("calathea_orbifolia", "calathea orbifolia plant with large rounded leaves decorated with metallic silver-green stripes"),
    ("calathea_medallion", "calathea medallion plant with ornate round leaves showing feather patterns and dark green halo"),
    ("calathea_rattlesnake", "calathea lancifolia rattlesnake plant with wavy upright pale green leaves and dark green spots"),
    ("calathea_zebrina", "calathea zebrina zebra plant with velvety emerald leaves and bold light lime stripes"),
    ("maranta_red_prayer", "maranta leuconeura red prayer plant with oval leaves and herringbone crimson red veins"),
    ("peace_lily", "spathiphyllum peace lily plant with lush deep green foliage and elegant white flower spathes"),
    ("anthurium_clari", "anthurium clarinervium plant with velvety dark heart leaves and crisp white crystalline veins"),
    ("anthurium_cryst", "anthurium crystallinum plant with large deep emerald heart foliage and shimmering silver veins"),
    ("anthurium_andra", "anthurium flamingo flower plant with glossy heart leaves and bright red waxy spathes"),
    ("philodendron_birkin", "philodendron birkin plant with dark green oval leaves accented by sharp creamy white pinstripes"),
    ("philo_heartleaf", "philodendron cordatum heartleaf vine with graceful cascading glossy green heart leaves"),
    ("philo_pink_princess", "philodendron pink princess plant with dark burgundy leaves and vivid bubblegum pink patches"),
    ("philo_white_knight", "philodendron white knight plant with dark foliage and bold pure white variegated blocks"),
    ("philo_micans", "philodendron hederaceum micans velvet plant with shimmering iridescent bronze-green leaves"),
    ("philo_xanadu", "philodendron xanadu plant with dense clumping upright stems and deeply lobed wavy leaves"),
    ("philo_selloum", "philodendron selloum hope plant with architectural deeply cut ruffled green fronds"),
    ("pothos_golden", "epipremnum aureum golden pothos vine with lush heart-shaped leaves marbled in warm yellow"),
    ("pothos_marble_queen", "epipremnum aureum marble queen pothos with heavy white and cream speckling on green leaves"),
    ("pothos_neon", "epipremnum aureum neon pothos with vibrant solid electric chartreuse lime leaves"),
    ("scindapsus_satin", "scindapsus pictus argyraeus satin pothos with matte dark green leaves splashed in silver"),
    ("alocasia_polly", "alocasia amazonica polly plant with dark metallic arrow leaves and prominent scalloped white veins"),
    ("alocasia_zebrina", "alocasia zebrina plant with iconic striped tiger stems and sharp upright arrow leaves"),
    ("alocasia_frydek", "alocasia micholitziana frydek green velvet plant with soft emerald leaves and bright white veins"),
    ("alocasia_stingray", "alocasia stingray plant with unique upward-cupped leaves tapering into long slender tails"),
    ("aglaonema_silver_bay", "aglaonema silver bay chinese evergreen with broad oval leaves washed in shimmering silver-gray"),
    ("aglaonema_red_siam", "aglaonema red siam plant with striking bright cherry-red margins and mottled pink-green foliage"),
    ("begonia_maculata", "begonia maculata polka dot begonia with olive angel wing leaves and crisp silver-white polka dots"),
    ("begonia_rex", "begonia rex painted leaf plant with spiraled ornamental leaves in metallic burgundy and silver"),
    ("peperomia_baby_rubber", "peperomia obtusifolia baby rubber plant with thick succulent rounded glossy jade green leaves"),
    ("string_of_turtles", "peperomia prostrata string of turtles with trailing cascading tiny leaves marked like turtle shells"),
    ("spider_plant", "chlorophytum comosum spider plant with arching ribbon leaves striped in green and white"),
    ("aspidistra_cast_iron", "aspidistra elatior cast iron plant with elegant upright dark green arching glossy leaves"),
    ("boston_fern", "nephrolepis exaltata boston fern with arching feathery fronds of soft ruffled green leaflets"),
    ("birds_nest_fern", "asplenium nidus birds nest fern with a central crown of glossy wavy apple-green fronds"),
    ("white_orchid", "phalaenopsis moth orchid plant with thick green leaves and arching stem of pure white blooms"),
    ("pilea_peperomioides", "pilea peperomioides chinese money plant with circular coin-shaped leaves radiating on stems"),
    ("stromanthe_triostar", "stromanthe sanguinea triostar plant with vivid leaves striped in cream, green and magenta-pink"),
    ("ctenanthe_fishbone", "ctenanthe burle-marxii fishbone prayer plant with silvery-green oval leaves and dark green herringbone marks"),
    ("fittonia_nerve_plant", "fittonia albivenis nerve plant with compact low mounded foliage and vivid white network veins"),
    ("hoya_sweetheart", "hoya kerrii sweetheart hoya succulent plant with thick fleshy heart-shaped green leaves"),
    ("hoya_hindu_rope", "hoya carnosa compacta hindu rope plant with thick twisted contorted succulent rope-like stems"),
    ("string_of_pearls", "senecio rowleyanus string of pearls succulent with delicate cascading strands of round beads"),
]

VARIATION_TEMPLATES = [
    "single potted {name}, healthy balanced foliage, centered full specimen in minimalist matte white ceramic pot",
    "single potted {name}, lush natural growth, centered full specimen in warm terracotta clay planter pot",
    "single potted {name}, clean architectural silhouette, centered full specimen in modern smooth concrete grey pot",
    "single potted {name}, dense compact foliage, centered full specimen in elegant dark charcoal stoneware pot",
    "single potted {name}, graceful organic habit, centered full specimen in textured beige artisanal ceramic pot",
    "single potted {name}, vibrant fresh leaves, centered full specimen in stylish fluted white ceramic planter",
    "single potted {name}, sculptural indoor foliage, centered full specimen in sleek cylindrical matte black pot",
    "single potted {name}, pristine botanical specimen, centered full specimen in smooth rounded cream pottery pot",
    "single potted {name}, neat attractive growth, centered full specimen in ribbed soft grey ceramic planter",
    "single potted {name}, elegant natural proportions, centered full specimen in unglazed sandy earthenware pot",
]


def build_manifest() -> dict:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    base_seed = 70000
    counter = 0

    # 50 Plants x 10 Variations = 500 items
    for sid, desc_base in DECOR_PLANTS:
        for v_idx, template in enumerate(VARIATION_TEMPLATES, start=1):
            counter += 1
            item_id = f"{sid}_{v_idx:02d}"
            desc = template.format(name=desc_base)
            if len(desc) > 240:
                raise ValueError(f"Description too long ({len(desc)} chars): {desc}")
            items.append({
                "id": item_id,
                "request": {
                    "operation": "generate",
                    "subject_type": "isolated_object",
                    "description": desc,
                    "seed": base_seed + counter,
                },
            })

    manifest = {
        "schema_version": 1,
        "max_attempts": 2,
        "items": items,
    }

    out_file = STAGING_DIR / "generation_batch.json"
    out_file.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(items)} items to {out_file}")
    return manifest


def main():
    manifest_data = build_manifest()
    batch_manifest = BatchManifest.model_validate(manifest_data)
    plan = build_batch_plan(batch_manifest, load_context(ROOT / "data"))
    plan_path = freeze_batch(plan, ROOT / "jobs" / "batches")
    print(f"Batch plan frozen: batch_id={plan['batch_id']}, items={len(plan['items'])}, path={plan_path}")


if __name__ == "__main__":
    main()
