---
name: plan-stock-job
description: Plan and run a single image job through this project's frozen router for generation, upscale or background removal. Use for structured stock-image requests, not batch execution.
---

# Plan a stock image job

Read `docs/phase-8-results.md` and the project phase rules in `AGENTS.md`. Prepare a structured JSON request with an explicit operation and subject type. Use `python scripts/router.py plan --request <file>` to freeze prompt, input hash, reviewed research and model choice before running anything. Inspect `jobs/<plan_id>/plan.json`, then use `python scripts/router.py run --plan jobs/<plan_id>/plan.json` to execute it. The run command checks for changed research, input and checkpoints and does no LLM or web research.

For glass or translucent background removal, expect a manual-review route with no automatic cutout. For other outputs, `completed_requires_review` still requires a human check of white/solid background quality, geometry, edges, shadow/reflection, text, labels, logos and branding before photostock submission. If the cache is stale or invalid, refresh research and create a new plan; do not bypass the cache gate.
