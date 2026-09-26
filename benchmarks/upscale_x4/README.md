# 4× upscale comparison

The ignored `2026-09-26/sample_comparison/models/<model-id>/` folders hold five full-resolution results per model. `sample_comparison/comparisons/` holds native crop sheets, and `results.json` points to the reorganized files. The older `x2double_fullset/` archive is retained locally because automatic deletion was rejected; it is not part of the active five-case comparison. The tracked conclusion and scope are in `docs/x4-upscale-evaluation-2026-09-26.md`. The chosen x4plus production route and its license/hash live in `data/upscaler_registry.json` and `data/license_registry.json`.

For a new model or system update, create a new dated run with fixed source images, same output scale, model revisions and license links, timing/VRAM, native-pixel center and edge sheets, and a tracked result document. Keep large trial images inside that run, never in project `output/`.
