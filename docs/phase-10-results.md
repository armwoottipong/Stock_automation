# Phase 10 hardening — 2026-09-26

## Recovery and integrity

The ComfyUI job runner now accepts a completed checkpoint only when it lists at least one existing output file. It rejects a mismatched stored job ID and records a stable error code instead of a server error body. The router validates the cached execution's plan ID, route, status and output files before reuse. A stale or mismatched execution record is replaced by running the frozen plan again (or recreating the manual-review record). Batch recovery still keeps its per-file checkpoints and bounded retry policy.

The router checks newly returned output files before writing a completed execution. Subprocess errors are categorized for retry decisions without embedding stderr or prompt text. ComfyUI HTTP and job-status errors likewise avoid reflecting server response bodies into exception messages. JSON event logs and batch reports carry status and error codes rather than prompts or raw exception text.

## Metrics and disk maintenance

Each new batch item records cumulative execution seconds and output bytes. The aggregate report includes total attempts, execution seconds and output bytes. Older item checkpoints lack timing data; aggregate `execution_seconds` is `null` for those batches. Existing output sizes are calculated from files when old checkpoints lack `output_bytes`. Metrics measure the local batch runner, not model quality or photostock suitability.

`python scripts\maintenance.py` previews disk capacity and stale `*.tmp` files in `jobs/`. `--apply` removes only listed files older than seven days; `--older-than-days` changes the threshold. The code checks resolved paths stay under the project's real `jobs/` directory and skips symlinks. It does not touch source images, models, finished outputs or checkpoints. On this machine, the preview found 0 eligible files and 91.1 GB free, so no live files were deleted.

## Verification and limits

`python -m pytest -q`: **59 passed**. New tests cover invalid completed checkpoints, secret-free job logs, bad cached execution records, scrubbed subprocess errors, metrics, maintenance preview/apply and an end-to-end frozen batch → router manual-review route. Replaying the existing three-item smoke batch returned two `completed_requires_review`, one `manual_review_required`, zero failures, three original attempts and 4,368,480 existing output bytes; no item was rerendered. Its historical execution time is unknown (`null`).

Security review covered subprocess invocation, HTTP error handling, checkpoint reuse, path-limited cleanup and structured log content. Frozen plans are checked by hashes and registry evidence but are not cryptographically signed against an attacker who can rewrite both plans and code. ComfyUI is a local service; production network exposure and authentication are outside this phase. Manual inspection remains required before stock submission. In particular, the current SDXL baseline has not met a literal-white-background quality gate, transparent subjects still require manual handling, and automated structural QC cannot clear text, logos, trademarks or branding.
