# Implementation plan

## Scope and design

Build a local, modular image pipeline. The control plane analyzes a request, checks cached research and licenses, selects a model stack, and freezes a job. The execution plane runs Python and ComfyUI with deterministic retry and script quality checks. Target hardware is Windows, RTX 4060, 8 GB VRAM. Commercial jobs exclude unclear or restricted licenses.

The supplied setup document is a requirements source. Its suggested model names and parameters are baselines, not verified recommendations. No model is selected until its source, license, hardware fit, and quality are checked.

## Phases

1. **Foundation (complete):** inspect OS, Python, CUDA, GPU, ComfyUI, models, nodes, workflows; create structure, validated config and registries, logging, tests.
2. **ComfyUI controller (complete):** isolated CUDA environment, health check, queue and monitor API jobs, collect outputs, status and checkpoint persistence, resume. Tests use a local fake HTTP server; a live API smoke job produced a 64×64 PNG and resume returned the same job.
3. **Generation (complete):** SDXL API workflow, prompt/parameter injection and script QC are implemented. The official SDXL Base checkpoint has a verified source, license, size and SHA-256; one 1024 px low-VRAM model smoke test passed. Generated label text was illegible, so this checkpoint is a functional baseline rather than a production quality recommendation.
4. **Upscale (complete):** pixel and creative CLI/workflows, guided filter, license-gated registries, pinned Ultimate SD Upscale node, Half Tile seam fix, tiled VAE decode and one-step low-VRAM tile retry are implemented. Live 1024-to-2048 pixel and 2048 creative smoke runs passed on the RTX 4060. Label text remained illegible; only one product image has been reviewed.
5. **Background research (complete):** compared BiRefNet DIS and BEN2 Base on seven locally generated Isolate object categories, with mixed scenes as a secondary check; verified official licenses, provenance and local CUDA/VRAM fit. BiRefNet is the provisional choice for opaque isolated subjects. Glass/translucent have no automatic path. The current SDXL fixtures came out gray despite white prompts, so literal-white performance and stock readiness remain unverified. See [Phase 5 results](phase-5-results.md).
6. **Background module (complete for opaque isolated objects):** pinned BiRefNet Python inference, conservative alpha clipping, frozen job records, checkpoint/license verification, white/solid input diagnostics and structural geometry/alpha QC. Glass and translucent subjects route to review without an automatic cutout. Every output requires visual review of edges, source shadow/reflection, text, logos and branding. See [Phase 6 results](phase-6-results.md).
7. **Research cache (complete):** offline lookup and reviewed update, 30-day maximum validity, registry/license revalidation and seeded Phase 4/5 decisions. Stale or invalid entries return no usable model. See [Phase 7 results](phase-7-results.md).
8. **Router (complete for structured requests):** validate task and subject, use fresh cache and registry decisions, build a stock-aware prompt, freeze model/input hashes and workflow settings, then execute only the saved plan. Transparent subjects route to manual review. See [Phase 8 results](phase-8-results.md).
9. **Batch (complete):** one frozen plan per batch with every item decision captured, sequential execution, file-level checkpoint/resume, bounded transient retry, live progress and final report. See [Phase 9 results](phase-9-results.md).
10. **Hardening (complete within local scope):** integration and resume tests, stricter completion checkpoints, stale temporary-file cleanup preview/apply, batch timing/output-size metrics, documentation and security review. See [Phase 10 results](phase-10-results.md).

Current pixel upscale behavior after the completed phases: 4× is the default with provisional RealESRGAN x4plus selection for isolated fruit; explicit 2× remains available. See [4× evaluation](x4-upscale-evaluation-2026-09-26.md). This does not change the historical Phase 4 smoke-test scope.

Current artifact placement is defined in the [artifact lifecycle](artifact-lifecycle.md): drafts in `staging/`, model/system comparisons in `benchmarks/`, and only reviewed submission packages in `output/`.

## Phase gates

Each phase requires tests and a smoke check before proceeding. Phase 2 must prove API health, queue, output retrieval, and resume. Phase 5 must finish before Phase 6 chooses a background model. Model and custom-node downloads require official provenance, license checks, and resource checks. The user has authorized installing necessary programs; this does not turn unverified models into approved production dependencies.
