"""Prepare 500 items batch: 300 plants (60 species x 5) + 200 mushrooms (40 species x 5)."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_image_automation.batch import BatchManifest, build_batch_plan, freeze_batch
from ai_image_automation.research_cache import load_context

SET_ID = "plants_mushrooms_500_2026-09-30_001"
STAGING_DIR = ROOT / "staging" / SET_ID

# 60 distinct plant species (foliage, trees, herbs, succulents, houseplants, palms, ferns)
PLANTS = [
    ("alocasia", "alocasia amazonica elephant ear plant with distinct white veins"),
    ("syngonium", "syngonium arrowhead vine plant with variegated arrow leaves"),
    ("ficus_benjamina", "ficus benjamina weeping fig branch with glossy green leaves"),
    ("areca_palm", "areca butterfly palm frond with delicate arching green leaflets"),
    ("dracaena", "dracaena marginata dragon tree with slender red edged green leaves"),
    ("money_tree", "pachira aquatica money tree with vibrant green palmate leaves"),
    ("staghorn_fern", "platycerium staghorn fern with bifurcated antler fronds"),
    ("maidenhair_fern", "adiantum maidenhair fern frond with delicate fan leaflets"),
    ("haworthia", "haworthia zebra succulent rosette with white horizontal stripes"),
    ("sedum", "sedum morganianum burros tail succulent trailing stems with plump leaves"),
    ("oregano", "fresh green oregano culinary herb sprig with aromatic leaves"),
    ("sage", "fresh culinary garden sage sprig with textured grey-green leaves"),
    ("cilantro", "fresh green cilantro coriander sprig with tender leaves"),
    ("parsley", "fresh curly parsley herb sprig with ruffled green leaflets"),
    ("lemongrass", "fresh green lemongrass stalk with aromatic slender leaves"),
    ("bamboo", "lucky bamboo stalk with fresh green shoots and leaves"),
    ("cast_iron_plant", "aspidistra cast iron plant with deep green glossy leaves"),
    ("corn_plant", "dracaena fragrans corn plant with broad striped green foliage"),
    ("chinese_evergreen", "aglaonema chinese evergreen plant with silver-green mottled leaves"),
    ("peperomia_watermelon", "watermelon peperomia leaf with green and silver curved stripes"),
    ("oxalis", "purple shamrock oxalis triangularis with delicate triangular leaves"),
    ("prayer_plant", "maranta prayer plant with decorative red veined patterned leaves"),
    ("kalanchoe", "kalanchoe succulent foliage with scalloped thick green leaves"),
    ("schefflera", "schefflera umbrella tree sprig with radiating glossy leaflets"),
    ("ponytail_palm", "beaucarnea ponytail palm with fountain-like slender leaves"),
    ("venus_flytrap", "dionaea muscipula venus flytrap with red-interior snap traps"),
    ("pitcher_plant", "nepenthes tropical pitcher plant with hanging green carnivorous pitcher"),
    ("air_plant", "tillandsia ionantha air plant rosette with spiky silvery leaves"),
    ("string_of_hearts", "ceropegia string of hearts trailing vine with heart shaped leaves"),
    ("lithops", "lithops living stones succulent split pebble with natural marbling"),
    ("monstera_adansonii", "monstera adansonii monkey mask leaf with natural oval fenestrations"),
    ("zebra_plant", "aphelandra zebra plant with bold white striped green foliage"),
    ("coleus", "coleus painted nettle leaf with vibrant burgundy and lime green edges"),
    ("fittonia", "fittonia nerve plant leaf with intricate bright red vein network"),
    ("african_violet", "african violet saintpaulia plant with velvety dark green leaves"),
    ("ti_plant", "cordyline fruticosa ti plant with vibrant magenta and green foliage"),
    ("english_ivy", "hedera helix english ivy vine with lobed variegated green leaves"),
    ("majesty_palm", "majesty palm frond with lush feathery tropical green leaflets"),
    ("parlor_palm", "chamaedorea parlor palm frond with elegant compact leaflets"),
    ("bay_laurel", "fresh sweet bay laurel leaf branch with aromatic glossy leaves"),
    ("dill", "fresh feathery green dill herb sprig with delicate fine leaves"),
    ("tarragon", "fresh french tarragon herb sprig with slender aromatic green leaves"),
    ("chives", "fresh green garden chives bunch with slender hollow blades"),
    ("ginger_plant", "zingiber officinale ginger foliage shoot with tropical green leaves"),
    ("curry_leaf", "murraya koenigii fresh aromatic curry leaf sprig"),
    ("pandan", "pandanus fragrant pandan leaf with long slender blade"),
    ("canna_lily_foliage", "canna lily foliage leaf with striking bronze-red stripes"),
    ("banana_leaf", "single fresh tropical banana leaf with smooth green surface"),
    ("taro_leaf", "colocasia taro elephant ear leaf with rich velvet green surface"),
    ("lotus_leaf", "single round green floating lotus leaf pad"),
    ("gingko_leaf", "single fan-shaped gingko biloba leaf with delicate veins"),
    ("olive_branch", "fresh green olive branch with silvery-backed green leaves"),
    ("ceropegia", "ceropegia succulent trailing stem with small plump leaves"),
    ("senecio_blue_chalk", "senecio blue chalksticks succulent with upright powder-blue leaves"),
    ("pencil_cactus", "euphorbia pencil cactus with cylindrical branching green stems"),
    ("golden_barrel_cactus", "echinocactus golden barrel cactus with ribbed sphere and yellow spines"),
    ("moon_cactus", "grafted moon cactus with bright red spherical top on green stem"),
    ("rhipsalis", "rhipsalis mistletoe cactus with cascading slender green stems"),
    ("epipremnum_cebu_blue", "cebu blue pothos leaf with metallic silvery-blue green sheen"),
    ("sansevieria_moonshine", "sansevieria moonshine snake plant with broad pale silvery-green leaves"),
]

# 40 distinct mushroom species (edible, gourmet, medicinal, wild, exotic)
MUSHROOMS = [
    ("shiitake", "shiitake mushroom with umbrella brown cap and cracked surface"),
    ("portobello", "large portobello mushroom with wide brown cap and exposed dark gills"),
    ("cremini", "cremini baby bella brown mushroom with round cap and stout stem"),
    ("white_button", "white button mushroom with smooth dome cap and clean white stem"),
    ("oyster_mushroom", "pearl oyster mushroom cluster with fan-shaped gray-white caps"),
    ("king_oyster", "king oyster mushroom with thick fleshy white stem and small tan cap"),
    ("chanterelle", "golden chanterelle mushroom with trumpet-shaped wavy yellow cap"),
    ("morel", "morel mushroom with conical honeycomb pitted tan-brown cap"),
    ("porcini", "porcini king bolete mushroom with thick club stem and rounded brown cap"),
    ("enoki", "enoki golden needle mushroom cluster with long slender white stems and tiny caps"),
    ("maitake", "maitake hen of the woods mushroom with frilly clustered gray-brown lobes"),
    ("shimeji", "brown beech shimeji mushroom cluster with round tan caps and crisp stems"),
    ("lion_mane", "lions mane mushroom with white icicle-like cascading spines"),
    ("reishi", "red reishi lingzhi mushroom with glossy kidney-shaped varnished cap"),
    ("cordyceps", "cordyceps militaris mushroom with bright orange finger-like club fruiting bodies"),
    ("turkey_tail", "turkey tail bracket fungus with concentric multicolored velvety bands"),
    ("chaga", "chaga mushroom conk with dark charcoal textured exterior and golden interior"),
    ("matsutake", "matsutake pine mushroom with thick white stem and brownish fibrous cap"),
    ("black_trumpet", "black trumpet mushroom with dark horn of plenty funnel shape"),
    ("fly_agaric", "amanita fly agaric mushroom with scarlet red cap and white raised spots"),
    ("death_cap", "amanita death cap mushroom with pale greenish cap and white stem skirt"),
    ("honey_fungus", "honey mushroom cluster with golden-brown dome caps and slender stems"),
    ("parasol_mushroom", "parasol mushroom with tall slender scaly stem and wide bell cap"),
    ("puffball", "giant puffball mushroom with smooth spherical white body"),
    ("blewit", "wood blewit mushroom with lilac-purple tinted cap and matching gills"),
    ("inky_cap", "shaggy mane inky cap mushroom with tall cylindrical scaly white cap"),
    ("lobster_mushroom", "lobster mushroom with vivid orange-red irregular textured surface"),
    ("golden_oyster", "golden oyster mushroom cluster with vibrant bright yellow caps"),
    ("pink_oyster", "pink oyster mushroom cluster with delicate ruffled pink caps"),
    ("blue_oyster", "blue oyster mushroom cluster with steel-blue shelf caps"),
    ("wood_ear", "wood ear jelly fungus with translucent brownish wavy cup shape"),
    ("snow_fungus", "snow fungus white jelly mushroom with frilly translucent blossom body"),
    ("cauliflower_mushroom", "cauliflower mushroom with brain-like frilly pale cream folds"),
    ("hedgehog_mushroom", "hedgehog sweet tooth mushroom with pale orange cap and spine-like teeth"),
    ("saffron_milk_cap", "saffron milk cap mushroom with concentric zoned orange cap"),
    ("birch_bolete", "birch bolete mushroom with rough scaly speckled stem and brown cap"),
    ("scarlet_cup", "scarlet elf cup mushroom with bright red interior saucer shape"),
    ("indigo_milk_cap", "indigo milk cap mushroom with vibrant deep indigo blue cap and gills"),
    ("amethyst_deceiver", "amethyst deceiver mushroom with deep purple-violet cap and gills"),
    ("glow_mushroom", "mycena night mushroom with translucent pale umbrella cap and slender stem"),
]

PLANT_TEMPLATES = [
    "fresh healthy {name}, centered full view",
    "single {name} viewed directly from top down",
    "side profile view of fresh {name}",
    "detailed view of {name} showing rich natural texture",
    "young fresh {name} with tender new growth",
]

MUSHROOM_TEMPLATES = [
    "fresh {name}, centered whole specimen view",
    "single {name} viewed directly from top down showing cap",
    "side profile view of {name} showing stem and cap gills",
    "cluster of fresh {name} showing natural organic formation",
    "young fresh {name} button specimen in pristine condition",
]


def build_manifest() -> dict:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    base_seed = 40000
    counter = 0

    # 1. 60 Plants x 5 = 300 items
    for sid, desc_base in PLANTS:
        for v_idx, template in enumerate(PLANT_TEMPLATES, start=1):
            counter += 1
            item_id = f"{sid}_{v_idx:02d}"
            desc = template.format(name=desc_base)
            items.append({
                "id": item_id,
                "request": {
                    "operation": "generate",
                    "subject_type": "isolated_object",
                    "description": desc,
                    "seed": base_seed + counter,
                },
            })

    # 2. 40 Mushrooms x 5 = 200 items
    for sid, desc_base in MUSHROOMS:
        for v_idx, template in enumerate(MUSHROOM_TEMPLATES, start=1):
            counter += 1
            item_id = f"{sid}_{v_idx:02d}"
            desc = template.format(name=desc_base)
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
