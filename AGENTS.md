# Project instructions

- For a new agent or production image task, follow `docs/agent-workflow.md` from intake through an audited platform package in `output/`. Complete generation, upscale/cutout, deterministic QC, color and format preparation, metadata and rights checks without any agent visual inspection or review gate. Package all structurally valid candidates with a contact sheet in staging for the user. Production manifests contain no image-review status or visual-review check. Run `scripts/audit_output.py` and deliver the output package; the user may inspect and delete unsuitable files afterward. Image inspection by the agent belongs only to model or system update benchmarks.
- When the user requests a new set, create new generation jobs and a separate staging/output identity. Do not satisfy it with previous renders or overwrite an older set without explicit direction.
- Deliver exactly one `output/<set-id>.zip` per requested set using `scripts/package_stock_set.py`. Put all requested formats and their platform-specific manifests inside that ZIP; keep prepared directories in staging, not at the top level of output.
- Follow `docs/implementation-plan.md` phase order. Phases 1–10 are complete within their documented scope. Do not treat later phases as implemented.
- Keep planning separate from execution: freeze job configuration, then let Python and ComfyUI run without LLM calls in the render loop.
- Read all six `data/*registry.json` files and `data/research_cache.json` before researching a model. Do not mark a model commercially usable without an official license source and verification date.
- Do not select a background removal default until the Phase 5 comparison and small benchmark are complete. Treat BiRefNet as one candidate only.
- Do not download models or install custom nodes without checking source, license, compatibility, disk space, and provenance. Record any installation in the registry.
- Preserve subject geometry when cutting out backgrounds. Default background policy is clean cutout, including original shadow and floor reflection removal.
- Stock candidates should exclude visible text, logos, trademarks and branding in prompts, but deterministic QC cannot prove their absence. The user may cull unsuitable images after delivery, including anatomy, cutout, shadow, similarity and metadata mismatches. Rework only when the user asks.
- Reusable project skill guides for tested workflows are in `.agents/skills/`; keep their scope aligned with completed phases.
- Validate configuration, keep structured logs free of secrets, and run tests after each phase.
