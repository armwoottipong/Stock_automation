---
name: run-stock-batch
description: Plan and run multiple stock-image jobs with this project's frozen batch runner, file checkpoints, bounded retry and progress report. Use for batches rather than single-image jobs.
---

# Run a stock image batch

Read `docs/phase-9-results.md` and `AGENTS.md`. Build one structured manifest with unique item IDs and explicit Phase 8 requests. Run `python scripts/batch.py plan --manifest <file>` and inspect the frozen plan before `python scripts/batch.py run --plan <batch_plan.json>`. The runner uses only frozen choices and executes files sequentially without LLM calls.

Use `python scripts/batch.py status --plan <batch_plan.json>` for progress and file-level outcomes. Re-run the same plan to resume pending work. Automatic retry is limited to transient errors; after correcting a failed item, `run --retry-failed` starts another bounded attempt round. Never interpret `completed_requires_review` as stock approval. Check each relevant output for background quality, intact geometry, edges, floor shadow/reflection and visible text, labels, logos or branding. Glass and translucent cutouts remain manual-review routes.
