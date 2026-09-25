# Implementation plan

## Scope and design

Build a local, modular image pipeline. The control plane analyzes a request, checks cached research and licenses, selects a model stack, and freezes a job. The execution plane runs Python and ComfyUI with deterministic retry and script quality checks. Target hardware is Windows, RTX 4060, 8 GB VRAM. Commercial jobs exclude unclear or restricted licenses.

The supplied setup document is a requirements source. Its suggested model names and parameters are baselines, not verified recommendations. No model is selected until its source, license, hardware fit, and quality are checked.

## Phases

1. **Foundation (complete):** inspect OS, Python, CUDA, GPU, ComfyUI, models, nodes, workflows; create structure, validated config and registries, logging, tests.
2. **ComfyUI controller (complete):** isolated CUDA environment, health check, queue and monitor API jobs, collect outputs, status and checkpoint persistence, resume. Tests use a local fake HTTP server; a live API smoke job produced a 64×64 PNG and resume returned the same job.
3. **Generation (complete):** SDXL API workflow, prompt/parameter injection and script QC are implemented. The official SDXL Base checkpoint has a verified source, license, size and SHA-256; one 1024 px low-VRAM model smoke test passed. Generated label text was illegible, so this checkpoint is a functional baseline rather than a production quality recommendation.
4. **Upscale:** pixel upscale, guided filter, ControlNet Tile, creative upscale, seam fix, tiled VAE, low-VRAM retry. Verify node repositories before install.
5. **Background research:** compare at most three candidates using official sources and a 1–3 image per category benchmark; check license, 8 GB fit, Windows/CUDA and ComfyUI/Python compatibility; record a default and fallback by subject type if needed.
6. **Background module:** segmentation, matte refinement, shadow/reflection policy, edge cleanup, geometry and alpha QC.
7. **Research cache:** lookup, staleness policy, update and reuse without research per job.
8. **Router:** task analysis, model and workflow selection, prompt builder, immutable job configuration.
9. **Batch:** one plan per batch, file-level checkpoint/retry, progress and report.
10. **Hardening:** integration tests, recovery, disk cleanup, metrics, documentation, security review.

## Phase gates

Each phase requires tests and a smoke check before proceeding. Phase 2 must prove API health, queue, output retrieval, and resume. Phase 5 must finish before Phase 6 chooses a background model. Model and custom-node downloads require official provenance, license checks, and resource checks. The user has authorized installing necessary programs; this does not turn unverified models into approved production dependencies.
