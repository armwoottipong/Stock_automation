# Phase 8 structured job router — 2026-09-25

## Planning and execution

`scripts/router.py plan --request <JSON>` validates an explicit operation and subject type. It looks up only fresh reviewed decisions from the Phase 7 cache, checks the model/license registry, builds an unbranded Isolate generation prompt when requested, and freezes the effective settings in `jobs/<plan_id>/plan.json`. The plan ID is a digest of the complete plan payload. Input image hashes, model revisions/hashes, research-entry hashes, workflow-template hash, prompt and parameters are recorded before execution. Creative upscale's existing one-step OOM fallback is also recorded. Replanning the same request returns the same plan; editing the frozen file is detected.

`scripts/router.py run --plan <plan.json>` rechecks research freshness, registry state, input hash and checkpoint hash, then calls an existing Python/ComfyUI workflow with the frozen arguments. No LLM, web search or model selection runs in the render loop. A changed input, model, license or research decision requires a new plan. Completed output remains `completed_requires_review` because structural QC cannot approve a photostock image.

The router requires structured intent instead of guessing from arbitrary prose:

| Operation | Subject type | Route |
| --- | --- | --- |
| `generate` | `isolated_object` | SDXL Base functional baseline with white/Isolate and no-brand prompt; image review required. |
| `upscale` | `pixel_2x` | Registered RealESRGAN x2plus ComfyUI workflow. |
| `creative_upscale` | `product_refine` | Registered SDXL checkpoint and xinsir Tile ControlNet workflow. |
| `remove_background` | `opaque_isolate` | Registered BiRefNet cutout workflow. |
| `remove_background` | `glass_isolate` or `translucent_isolate` | Manual review record; no automatic cutout. |

Example request files:

```json
{"operation":"generate","description":"matte blue ceramic mug","seed":618}
```

```json
{"operation":"remove_background","subject_type":"opaque_isolate","input":"path/to/object.png"}
```

The generation baseline still often makes gray gradients despite white prompts. The planner blocks explicit text/logo/brand terms in positive prompts and adds stock exclusions to negative prompts, but it cannot identify arbitrary brand names or certify an image visually. Final review must reject visible text, labels, trademarks, logos, branding, altered geometry, unwanted shadows and other artifacts.

## Smoke checks and limits

The frozen router plan executed a 1024→2048 pixel upscale through a live ComfyUI server. Its output passed existing structural QC, which still required stock review. An opaque-mug cutout plan reused the verified Phase 6 result, and a glass plan produced no output and returned `manual_review_required`. Generation and creative upscale were validated at planning/command level; their underlying workflows had prior Phase 3–4 smoke runs, but were not rerun through this router in Phase 8. Tests cover route selection, prompt exclusions, plan tampering, cache expiry, input changes and creative parameter forwarding.

Phase 8 plans one file at a time. Phase 9 adds batch-level planning, checkpoints, retry and reporting.
