# Benchmarks: model overview

This folder contains **model decisions and repeatable comparisons**. Large source images and full-resolution outputs stay local and Git-ignored. The compact comparison images below are tracked, so another agent can understand the decisions immediately after cloning. None of these images is a stock deliverable.

| Task | Current route | Compared models | Quick view | Reviewed decision |
| --- | --- | --- | --- | --- |
| White-background object generation | **FLUX.2 Klein 4B FP8**, provisional | Klein vs SDXL Base 1.0 | [Four-case sheet](comparisons/generation-2026-09-26.jpg) | [Result](../docs/generation-model-refresh-2026-09-26.md) |
| Opaque background removal | **BiRefNet DIS**, provisional | BiRefNet vs BEN2 Base | [Source and cutouts](comparisons/background-2026-09-25.jpg) | [Result](../docs/phase-5-results.md) |
| Pixel upscale | **RealESRGAN x4plus** at 4×, provisional | x4plus once vs x2plus twice | [Center](comparisons/upscale-center-2026-09-26.jpg) · [Edges](comparisons/upscale-edge-2026-09-26.jpg) | [Result](../docs/x4-upscale-evaluation-2026-09-26.md) |
| Creative upscale | SDXL + xinsir Tile ControlNet | Functional route, no new head-to-head sheet | [Model cards](models/README.md) | [Phase 4 result](../docs/phase-4-results.md) |

## Find a model

[All 10 registered model and component cards](models/README.md) show their role, selection status, license, checkpoint and result link. The [comparison gallery](comparisons/README.md) explains each visual sheet. Models without commercial clearance are marked explicitly.

## Raw evidence and future updates

| Experiment | Frozen inputs / metrics | Full local results |
| --- | --- | --- |
| Generation, 2026-09-26 | [`cases.json`](generation/2026-09-26/cases.json), [`run.json`](generation/2026-09-26/run.json) | `generation/2026-09-26/output/<model-id>/` |
| Background removal, Phase 5 | [`isolated_cases.json`](background/isolated_cases.json), [`cases.json`](background/cases.json) | `background/output/isolated/<model-id>/` and `background/output/scene/<model-id>/` |
| 4× upscale, 2026-09-26 | [Five-fruit result](../docs/x4-upscale-evaluation-2026-09-26.md) | `upscale_x4/2026-09-26/sample_comparison/models/<model-id>/` and `comparisons/` |

Run `python scripts/build_benchmark_previews.py` to refresh the four compact images from local raw evidence, then `python scripts/build_benchmark_catalog.py` to refresh model cards after a reviewed registry change. For a new comparison, create a dated case manifest, run candidates on the same inputs, inspect full-size results, update the reviewed result document, then change the registry/cache and model cards. Existing generation and background runners are documented in their task folders. Do not use production `output/` for experiments.

**Local cleanup still pending:** `upscale_x4/2026-09-26/x2double_fullset/` contains 79 legacy files from the earlier 25-image run. It is outside the active five-case comparison and ignored by Git. Automatic approval review rejected its deletion, so this folder needs manual removal on this machine if it is no longer wanted.
