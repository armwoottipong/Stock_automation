"""Generate the 200 flower items manifest for 40 species x 5 variations."""

import json
from pathlib import Path

FLOWERS = [
    ("rose", "red rose"),
    ("sunflower", "yellow sunflower"),
    ("tulip", "pink tulip"),
    ("orchid", "purple phalaenopsis orchid"),
    ("daisy", "white daisy flower with yellow center"),
    ("lily", "white lily bloom"),
    ("lotus", "pink sacred lotus blossom"),
    ("hibiscus", "vibrant red hibiscus flower"),
    ("lavender", "purple lavender flower blossom sprig"),
    ("peony", "soft pink peony blossom"),
    ("hydrangea", "blue hydrangea flower bloom cluster"),
    ("carnation", "red carnation bloom"),
    ("marigold", "bright orange marigold flower"),
    ("jasmine", "white jasmine blossom"),
    ("frangipani", "white and yellow frangipani plumeria bloom"),
    ("cherry_blossom", "pink cherry blossom flower"),
    ("dandelion", "yellow dandelion flower bloom"),
    ("gerbera", "orange gerbera daisy flower"),
    ("iris", "deep blue iris blossom"),
    ("daffodil", "bright yellow daffodil narcissus flower"),
    ("poppy", "red oriental poppy flower bloom"),
    ("chrysanthemum", "yellow chrysanthemum bloom"),
    ("dahlia", "magenta dahlia flower bloom"),
    ("camellia", "pink camellia blossom"),
    ("magnolia", "white magnolia flower bloom"),
    ("bird_of_paradise", "orange and blue bird of paradise flower"),
    ("anemone", "white anemone flower with black center"),
    ("freesia", "yellow freesia flower blossom"),
    ("violet", "purple violet flower bloom"),
    ("gardenia", "white gardenia flower bloom"),
    ("begonia", "red begonia flower bloom"),
    ("morning_glory", "blue morning glory trumpet flower"),
    ("zinnia", "pink zinnia flower bloom"),
    ("cosmos", "pink cosmos flower bloom"),
    ("bougainvillea", "magenta bougainvillea flower cluster"),
    ("anthurium", "red anthurium flamingo flower"),
    ("ranunculus", "orange ranunculus flower blossom"),
    ("amaryllis", "red amaryllis flower bloom"),
    ("gladiolus", "pink gladiolus flower bloom"),
    ("water_lily", "white water lily blossom"),
]

VARIATIONS = [
    ("full_bloom", "fresh {flower} in full open blossom"),
    ("top_view", "single {flower} viewed directly from top down"),
    ("side_profile", "side profile view of a blooming {flower}"),
    ("with_stem", "{flower} with natural green stem and leaves"),
    ("opening_bud", "fresh {flower} bud gently opening into blossom"),
]


def build_manifest() -> dict:
    items = []
    base_seed = 20000
    counter = 0

    for flower_id, flower_name in FLOWERS:
        for var_idx, (var_key, template) in enumerate(VARIATIONS, start=1):
            counter += 1
            item_id = f"{flower_id}_{var_idx:02d}"
            desc = template.format(flower=flower_name)
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

    return {
        "schema_version": 1,
        "max_attempts": 2,
        "items": items,
    }


def main():
    manifest = build_manifest()
    out_path = Path("staging/flowers_200_2026-09-29/generation_batch.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Generated manifest with {len(manifest['items'])} items at {out_path}")


if __name__ == "__main__":
    main()
