# Project instructions

- Follow `docs/implementation-plan.md` phase order. Phases 1–4 are complete. Do not treat later phases as implemented.
- Keep planning separate from execution: freeze job configuration, then let Python and ComfyUI run without LLM calls in the render loop.
- Read all seven `data/*registry.json` files before researching a model. Do not mark a model commercially usable without an official license source and verification date.
- Do not select a background removal default until the Phase 5 comparison and small benchmark are complete. Treat BiRefNet as one candidate only.
- Do not download models or install custom nodes without checking source, license, compatibility, disk space, and provenance. Record any installation in the registry.
- Preserve subject geometry when cutting out backgrounds. Default background policy is clean cutout, including original shadow and floor reflection removal.
- Validate configuration, keep structured logs free of secrets, and run tests after each phase.
