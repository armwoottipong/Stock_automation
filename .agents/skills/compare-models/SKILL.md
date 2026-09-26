---
name: compare-models
description: Compare background removal model candidates for this photostock project using registered provenance, licenses, local benchmarks and visual cutout review. Use when selecting or revisiting a model, not for production image removal.
---

# Compare background removal models

Work from the repository root. Follow `AGENTS.md` and the current phase in `docs/implementation-plan.md`. Read all six `data/*registry.json` files and `data/research_cache.json` before researching a new candidate. Require an official license source and verification date before calling it commercially usable; check checkpoint source, hash, compatibility, disk and VRAM before any installation.

Use `docs/phase-5-results.md` as the existing baseline. For a new comparison, freeze one manifest and run every candidate on the same files and preprocessing. Prefer unbranded objects on white or simple solid backgrounds because these are the target inputs. Record the actual background color; a white prompt alone does not prove a white image. Keep glass and translucent objects separate from opaque subjects.

The Phase 5 scripts are in `scripts/benchmark_background.py` and `scripts/review_background_benchmark.py`; frozen Isolate settings and metadata are in `benchmarks/background/isolated_generation.json` and `isolated_cases.json`. Inspect masks and cutouts against white, dark and checkerboard, with attention to fine structure, shape, edge halo, retained source background, and removal of original shadow/reflection. Measure runtime and peak VRAM on the target GPU. Avoid claiming general accuracy from this small, unlabelled set.

Do not promote a candidate to a production default until the benchmark and project phase gate pass. Final stock-content review must reject text, logos, trademarks, labels and branding. Record findings and limitations in docs and registries, then run project tests.
