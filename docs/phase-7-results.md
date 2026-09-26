# Phase 7 reviewed research cache — 2026-09-25

## Behavior

`src/ai_image_automation/research_cache.py` reads and validates all six `data/*registry.json` files plus `data/research_cache.json`, then returns an offline decision for a `(task, subject_type)` key. It makes no network requests and does not invoke an LLM. The CLI is `scripts/research_cache.py` with `lookup`, `list` and `upsert` actions. Phase 8 can call the same lookup before freezing a job configuration.

Every entry has unique candidate IDs, HTTPS evidence links, a reviewed outcome, verification date and expiry date. Validity is limited to 30 days, inclusive. A selected model also needs a local benchmark document, an installed eligible model record, matching official model/license sources in the entry, and matching verification dates in the model and license registries. Missing, expired or invalid entries return **no usable model ID**. The cache never upgrades a model's commercial eligibility by itself.

The seeded records reuse completed project research: SDXL for Isolate generation, xinsir ControlNet for creative upscale, BiRefNet DIS for opaque Isolate cutouts, manual review for glass and sheer cutouts, and RealESRGAN x2plus for pixel 2×. They were verified on 2026-09-25 and expire after 2026-10-25. These are narrow functional decisions; they do not certify photostock quality or supply a transparent-object default.

## Commands

```powershell
python scripts\research_cache.py list
python scripts\research_cache.py lookup --task remove_background --subject opaque_isolate
python scripts\research_cache.py lookup --task remove_background --subject glass_isolate
python scripts\research_cache.py upsert --entry path\to\reviewed-entry.json
```

`upsert` replaces only the matching task/subject entry and writes the JSON file atomically. Before updating a selected entry, recheck the official model and license sources, update their registry verification dates, and record the actual benchmark document. The updater validates evidence links and dates but cannot determine whether a web page is truly official or whether a benchmark conclusion is sound; those remain reviewer responsibilities. Do not place credentials or private notes in this cache.

## Verification and limits

Local tests cover fresh, missing, expired, changed-license and duplicate-key cases, plus updates that preserve other entries. CLI smoke lookup and list returned the reviewed decisions. This phase implements cache maintenance only; existing Phase 3–6 commands still use their own registry checks and do not silently change model choices from this cache.
