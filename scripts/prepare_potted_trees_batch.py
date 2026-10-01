"""Prepare 500 items batch: 50 potted tree species x 10 variations."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_image_automation.batch import BatchManifest, build_batch_plan, freeze_batch
from ai_image_automation.research_cache import load_context

SET_ID = "potted_trees_500_2026-10-01_001"
STAGING_DIR = ROOT / "staging" / SET_ID

# 50 distinct potted tree species (indoor trees, ficus, bonsai, palms, citrus, conifers, woody houseplants)
TREES = [
    ("ficus_lyrata", "fiddle leaf fig tree with large violin-shaped dark green leaves"),
    ("ficus_benjamina", "weeping fig tree with arching branches and glossy oval leaves"),
    ("ficus_elastica_burgundy", "burgundy rubber tree with bold glossy dark green leaves"),
    ("ficus_audrey", "ficus audrey banyan tree with velvety emerald leaves and prominent veins"),
    ("ficus_microcarpa_bonsai", "ginseng ficus bonsai tree with sculptural exposed roots"),
    ("ficus_ali", "narrow leaf fig tree with slender drooping willow-like leaves"),
    ("ficus_triangularis", "triangle fig tree with unique heart-triangle shaped green leaves"),
    ("dracaena_marginata", "madagascar dragon tree with slender trunk and arching red-edged narrow leaves"),
    ("dracaena_fragrans", "corn plant tree with stout cane trunk and broad arching leaves"),
    ("dracaena_reflexa", "song of india tree with multi-stemmed woody trunk and vibrant lime-green leaves"),
    ("pachira_aquatica", "money tree with braided woody trunk and five-lobed green palmate leaves"),
    ("beaucarnea_recurvata", "ponytail palm tree with bulbous base and fountain of slender curving leaves"),
    ("schefflera_arboricola", "dwarf umbrella tree with compact umbrella whorls of glossy green leaflets"),
    ("schefflera_actinophylla", "australian umbrella tree with radiating dark green glossy palmate leaflets"),
    ("yucca_elephantipes", "spineless yucca tree with thick architectural woody cane and sword leaves"),
    ("polyscias_fruticosa", "ming aralia tree with gnarled twisting trunk and delicate feathery foliage"),
    ("polyscias_scutellaria", "shield aralia tree with upright slender stem and rounded glossy leaves"),
    ("olea_europaea", "mediterranean olive tree with gnarled silvery bark and grey-green leaves"),
    ("citrus_limon", "indoor meyer lemon tree with glossy oval leaves and small green citrus"),
    ("citrus_calamondin", "calamondin orange tree with compact canopy of dark leaves and miniature citrus"),
    ("laurus_nobilis", "sweet bay laurel topiary tree with neatly rounded lollipop canopy"),
    ("bucida_buceras", "shady lady black olive indoor tree with delicate tiered branches and tiny leaves"),
    ("radermachera_sinica", "china doll tree with glossy emerald bipinnate leaves and delicate texture"),
    ("murraya_paniculata", "orange jasmine tree with dense canopy and fragrant glossy leaflets"),
    ("coffea_arabica", "arabian coffee tree with shiny dark green wavy leaves on upright woody stem"),
    ("adenium_obesum", "desert rose bonsai tree with swollen succulent caudex and leathery leaves"),
    ("crassula_ovata", "jade plant tree bonsai with thick branching trunk and plump glossy jade leaves"),
    ("crassula_gollum", "gollum jade bonsai tree with woody succulent trunk and tubular green leaves"),
    ("portulacaria_afra", "elephant bush bonsai tree with reddish woody stems and tiny rounded leaves"),
    ("juniperus_procumbens", "japanese garden juniper bonsai tree with curved trunk and needle foliage"),
    ("pinus_thunbergii", "japanese black pine bonsai tree with rugged bark and dark green needles"),
    ("pinus_parviflora", "japanese white pine bonsai tree with gnarled trunk and bluish-green needles"),
    ("acer_palmatum", "japanese maple bonsai tree with slender branches and five-lobed green leaves"),
    ("ulmus_parvifolia", "chinese elm bonsai tree with cork bark and small serrated green leaves"),
    ("carmona_microphylla", "fukien tea bonsai tree with gnarled grey trunk and shiny bristled leaves"),
    ("serissa_foetida", "snowrose bonsai tree with exposed twisted root base and tiny oval leaves"),
    ("podocarpus_macrophyllus", "buddhist pine indoor tree with slender trunk and needle-like strap foliage"),
    ("araucaria_heterophylla", "norfolk island pine tree with symmetrical tiered branches and soft needles"),
    ("chamaedorea_elegans", "parlor palm tree with slender cane stems and arching feathery fronds"),
    ("rhapis_excelsa", "lady palm tree with slender bamboo-like stalks and fan-shaped split glossy leaflets"),
    ("howea_forsteriana", "kentia palm tree with tall arching graceful feathered fronds"),
    ("dypsis_lutescens", "areca butterfly palm tree with golden cane stems and upright arching leaflets"),
    ("cycas_revoluta", "sago palm tree with rugged cylindrical trunk and radiating feather-like fronds"),
    ("euphorbia_tirucalli", "pencil cactus tree with architectural trunk and dense crown of cylindrical stems"),
    ("euphorbia_ingens", "candelabra cactus tree with massive fluted ribbed upright succulent branches"),
    ("pachypodium_lamerei", "madagascar palm tree with thick spiny silvery trunk and tuft of long leaves"),
    ("jacaranda_mimosifolia", "potted jacaranda seedling tree with single trunk and feathery bipinnate leaves"),
    ("eucalyptus_gunnii", "cider gum eucalyptus tree with reddish stem and powdery silver-blue coin leaves"),
    ("ginkgo_biloba", "potted ginkgo tree with slender upright trunk and distinct fan-shaped leaves"),
    ("betula_pendula", "miniature silver birch tree with chalk-white bark trunk and green serrated leaves"),
]

VARIATION_TEMPLATES = [
    "single potted {name}, slender upright single trunk, sparse natural branches, simple matte white ceramic pot",
    "single potted {name}, elegant gently curved trunk, foliage on upper canopy, minimalist terracotta planter pot",
    "single potted {name}, clean architectural silhouette, balanced natural branches, modern grey cylindrical pot",
    "single potted {name}, compact pruned canopy, realistic lush green leaves, classic round stoneware pot",
    "single potted {name}, tall slender indoor specimen, airy open branching, smooth beige earthenware pot",
    "single potted {name}, young upright sapling tree, fresh tender green growth, fluted white ceramic pot",
    "single potted {name}, sculpted formal bonsai growth habit, twisted woody trunk, shallow glazed ceramic planter",
    "single potted {name}, full specimen view including pot, vibrant green foliage, ribbed matte charcoal pot",
    "single potted {name}, graceful branching canopy, natural organic proportions, unglazed sand colored pottery",
    "single potted {name}, stately indoor decorative tree, dense glossy foliage, minimalist geometric stone planter",
]


def build_manifest() -> dict:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    base_seed = 60000
    counter = 0

    # 50 Trees x 10 Variations = 500 items
    for sid, desc_base in TREES:
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
