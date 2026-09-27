---
name: run-stock-batch
description: Plan and run multiple stock-image jobs with this project's frozen batch runner, file checkpoints, bounded retry and progress report. Use for batches rather than single-image jobs.
---

# Run a stock image batch

Read `docs/agent-workflow.md`, `docs/phase-9-results.md` and `AGENTS.md`. Build one structured manifest with unique item IDs and explicit Phase 8 requests. Run `python scripts/batch.py plan --manifest <file>` and inspect the frozen plan before `python scripts/batch.py run --plan <batch_plan.json>`. The runner uses only frozen choices and executes files sequentially without LLM calls. A batch handles one operation per item; chain generation, upscale and cutout with new batches using structurally valid prior outputs. For a production request, continue through color/format, metadata and rights checks, then package all structurally valid files in `output/` and run `scripts/audit_output.py`. Production has no agent image-inspection step or review-status field; the user may cull unsuitable files after delivery.

Use `python scripts/batch.py status --plan <batch_plan.json>` for progress and file-level outcomes. Re-run the same plan to resume pending work. Automatic retry is limited to transient errors; after correcting a failed item, `run --retry-failed` starts another bounded attempt round. `completed` means automated execution and deterministic QC finished; it does not claim platform acceptance. Automated checks cover file integrity, dimensions, alpha, margins and metadata. Glass and translucent cutouts return `unsupported_subject` because no automatic cutout exists; do not count those items as prepared files.
