# Background-removal comparison

`isolated_generation.json` freezes the seven white-background fixture prompts. `isolated_cases.json` lists those local files and drives the primary BiRefNet/BEN2 comparison. `cases.json` is the earlier mixed-scene robustness set. Inputs live in ignored `input/`; model results are separated as `output/isolated/<model-id>/` and `output/scene/<model-id>/`, and local visual sheets are in `output/comparisons/`. The measured decision is in `docs/phase-5-results.md`.

From the project root, rerun a model with `python scripts/benchmark_background.py --manifest isolated_cases.json --model birefnet-dis` or `--model ben2-base`, then build review sheets with `python scripts/review_background_benchmark.py --manifest isolated_cases.json`. Use a new dated generation benchmark for future generator changes; do not overwrite these pinned removal fixtures.
