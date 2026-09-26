# Phase 9 frozen batch execution — 2026-09-26

## Workflow

`scripts/batch.py plan` validates the **entire** structured manifest and records every Phase 8 item plan within one immutable `batch_plan.json`. Model, research, prompt, input hash and workflow choices are frozen before execution; there is no LLM or web lookup in the render loop. Items run sequentially to fit the RTX 4060. Mixed operations are allowed.

Example `batch.json`:

```json
{
  "schema_version": 1,
  "max_attempts": 2,
  "items": [
    {"id": "mug_upscale", "request": {"operation": "upscale", "input": "input/mug.png"}},
    {"id": "glass_review", "request": {"operation": "remove_background", "subject_type": "glass_isolate", "input": "input/glass.png"}}
  ]
}
```

Input paths in the manifest are resolved from the shell's working directory; run the commands from the repository root. IDs are unique lowercase names with letters, numbers, `_` or `-`. A batch accepts 1–1000 items and `max_attempts` from 1 to 3.

```powershell
python scripts\batch.py plan --manifest batch.json
python scripts\batch.py run --plan jobs\batches\BATCH_ID\batch_plan.json
python scripts\batch.py status --plan jobs\batches\BATCH_ID\batch_plan.json
```

The runner stores per-item checkpoints in `items/`, aggregate `progress.json` and `report.json`, and prompt-free event records in `events.jsonl` beside the batch plan. The CLI prints progress while running. Repeating `run` skips completed items whose outputs still exist. A process interrupted while an item is `running` resumes that attempt; existing Phase 8 and ComfyUI job records are reused when they are intact. An OS-held lock prevents two processes from running the same batch simultaneously.

Only transient timeout, connection and CUDA OOM errors retry automatically, with at most the frozen `max_attempts`. Deterministic failures become file-level `failed` records, and later items continue. `run --retry-failed` explicitly starts a new bounded attempt round for failed items after the cause is addressed. Reports contain error codes and types, not prompt text or raw exception messages. The command exits with code 2 when any item remains failed.

## Local verification

Unit tests cover tampering, duplicate IDs, checkpoint resume, transient retry, permanent failure isolation, interruption recovery, explicit retry and missing completed output. A three-item mixed smoke batch completed with two `completed_requires_review`, one `manual_review_required`, and zero failures. The two generated output paths reused verified Phase 8/6 jobs; this was an orchestration smoke, not a new image-quality benchmark. Repeating the batch left all item attempt counts at one.

`completed_requires_review` does not mean photostock approval. Inspect white/solid background quality, geometry, cutout edges, shadow/reflection, text, labels, logos and branding for every relevant output. Generation still needs better white-background acceptance; transparent objects still have no automatic cutout path.
