# Agent runbook: from request to stock package

Last reviewed: 2026-09-26. This is the entry point for an agent operating the **existing** local pipeline. Read `AGENTS.md` first, then this file, `docs/implementation-plan.md`, `docs/artifact-lifecycle.md`, and the relevant `.agents/skills/<name>/SKILL.md`. The repository implements Phases 1–10 within their documented limits. A phase marked complete does not mean an image is approved by a stock platform.

## 1. Operating contract

The project makes unbranded, isolated objects, preferably on a white or simple solid background. **A production job finishes with a technically prepared, audited platform package in `output/`.** Production has no agent image-inspection step, visual review gate, or review-status field. Run frozen generation and deterministic checks without opening the images in the agent. Complete technical, color, rights and metadata preparation, then package every structurally valid candidate. A request for 25 images means 25 technically prepared files in the delivered package. Provide a contact sheet and inventory for the user, who may inspect and delete unsuitable files afterward. Rework only if the user asks. A request for a new set requires new generation jobs and separate artifact paths; do not reuse prior renders or overwrite the prior set without explicit direction. Visual image inspection by the agent is reserved for model or system update benchmarks in Section 5.

Planning and execution are separate. An agent may interpret the brief, check research and policy, create structured JSON, and inspect structured execution results. `router.py plan` or `batch.py plan` freezes model choices, prompt, source hashes and workflow settings. `run` then executes the frozen plan through Python/ComfyUI without an LLM or web call in the render loop. Editing source files, checkpoints, registries or research after planning requires a **new** plan. Keep one GPU job at a time on the RTX 4060 8 GB machine.

The current route choices are narrow:

| Operation | Current implementation | Important limit |
| --- | --- | --- |
| Generate isolated object | FLUX.2 Klein 4B distilled FP8 at 4 steps, CFG 1 | Provisional local winner over SDXL on four white-background cases. |
| Pixel upscale | RealESRGAN x4plus at **4× by default**; explicit x2plus at 2× | 4× selection is provisional from a five-fruit comparison. |
| Creative upscale | SDXL + xinsir Tile ControlNet | May change object geometry. Use only if the brief allows creative refinement. |
| Remove opaque background | BiRefNet DIS, clean cutout without original shadow/floor reflection | Provisional opaque route; save previews for the user without an agent inspection step. |
| Remove glass/translucent background | `unsupported_subject`; no automatic cutout | Do not relabel these subjects as opaque. |

No command automatically clears visible text, logos, trademarks, branding, anatomical errors, excessive similarity or stock acceptance. `completed` means the frozen operation and deterministic QC finished; continue production through `output/`. The user handles visual selection after delivery. The metadata catalog must record true origin (`generative_ai` or `camera_photo`). Buyer-facing titles and keywords describe the subject; keep provenance in the catalog and complete any platform disclosure in its portal. As checked on 2026-09-26, [Adobe requires its generative-AI disclosure and rights review](https://helpx.adobe.com/stock/contributor/submit-your-content/submit-generative-ai-content/submit-generative-ai-content.html); [Shutterstock does not accept contributor AI-generated content](https://submit.shutterstock.com/help/en/articles/10594622-content-policy-updates-ai-generated-content). Recheck official rules immediately before submission.

## 2. Where every artifact goes

| Directory | Contents and retention |
| --- | --- |
| `input/` | User-supplied originals. Record source and rights; do not overwrite. |
| `jobs/<id>/` | Frozen single plans, requests, ComfyUI workflow, raw outputs, execution record and deterministic QC. |
| `jobs/batches/<id>/` | Frozen batch plan, per-item checkpoints, progress, report and safe event log. |
| `staging/<set>/` | Candidate images, metadata, previews, contact sheets and preparation evidence. |
| `staging/<set>/packages/` | Prepared internal packages before copying into the final set folder. |
| `benchmarks/` | Controlled model comparisons and system-update experiments, with test inputs, outputs, runtime/VRAM and visual sheets. |
| `logs/` | Runtime diagnostics. No secrets or final deliverables. |
| `output/<set-id>/` | Exactly one audited folder per request, containing platform assets and any companion formats with their own manifests. No ZIP delivery. |
| `data/` | Model/tool/license registries and reviewed research cache. Model weights are local under ignored `vendor/`. |

Large local images, models, `jobs/`, `staging/` contents and benchmark outputs are Git-ignored. A fresh clone or separate worktree does **not** contain them. See `docs/agent-usage.md` before handing execution to another agent or machine.

## 3. New production job: complete sequence

1. **Intake.** Record subject, count, distinct variants, intended platform, true source type, white/solid or transparent deliverable, aspect ratio, resolution, allowed props, exclusions and commercial rights. For generated stock work, do not request text, labels, logos, trademarks or branding. For a real photo, keep truthful `camera_photo` provenance. Select a platform the source type permits.
2. **Preflight.** From the repository root, check `git status --short`, disk, Python/CUDA environment, validated settings (`python -c "from ai_image_automation.config import load_settings; print(load_settings().model_dump_json())"`), `python controller.py health`, and `python scripts/research_cache.py list`. Confirm the relevant selected entry is fresh and the local checkpoint hash/license matches its registry. The cache is evidence, not permission to ignore a platform rule. Start ComfyUI with `./scripts/start_comfyui.ps1` if needed. Use `python -m pytest -q` after a code/configuration change.
3. **Create a structured request.** For one operation use `scripts/router.py plan --request <JSON>`. For 2–1000 independent items use `scripts/batch.py plan --manifest <JSON>`. Inspect the frozen `plan.json` or `batch_plan.json`: operation, subject, prompt exclusions, model, scale, input hash, research freshness and route. Do not assume free-form text invokes upscale or cutout automatically. In a multi-step job, feed the structurally valid output of one step into a **new** plan for the next step.
4. **Run and checkpoint.** Execute the saved plan, read `execution.json` and the underlying `jobs/<job_id>/qc.json`. For batches, use `status` and `report.json`. A repeat `run` resumes or reuses valid completed work. Automatic retries cover only bounded transient failures; fix deterministic failures, then use `run --retry-failed` when appropriate.
5. **Validate source render structurally.** Check job success, dimensions, file integrity, prompt exclusions and measurable background/margins. White/solid input makes cutout easier. Continue without agent visual inspection.
6. **Upscale as requested.** For the default, plan `{"operation":"upscale","input":"..."}` (4×). Check status and dimension change programmatically. Choose 2× explicitly only when appropriate.
7. **Remove background when the deliverable calls for transparency.** Plan `remove_background` with `subject_type: opaque_isolate`. Run deterministic alpha, transparency, margin and file checks; save white, dark and checkerboard previews for the user. Glass and sheer material return `unsupported_subject` because there is no automatic cutout. If the deliverable is an opaque white image, preserve that image; a cutout is not automatically required.
8. **Stage candidates.** Copy structurally valid raw results to a named `staging/<set>/` folder, keeping provenance back to plan/job IDs. Do not move `jobs/` checkpoints. Use filenames, prompts and hashes for grouping. Check source rights, any releases, tool/model commercial terms and platform eligibility.
9. **Prepare platform file.** Confirm dimensions, file type, color space/profile, transparency or white-background specification, size and alpha quality against **current** official platform requirements. Adobe's current [transparent PNG requirements](https://helpx.adobe.com/stock/contributor/submit-your-content/submit-pngs/technical-requirements-png-submission.html) include 4–100 MP, at most 45 MB, sRGB and actual transparency. A file with no ICC profile must not be marked as color-verified solely because it looks correct. Use a color-managed conversion step, then verify the exported file. A white-background upload may need different photo-format preparation. The project has no automatic final color conversion or portal uploader.
10. **Write and embed metadata.** Make an English catalog with exact staged filenames, descriptive titles based on the prompt and ordered relevant keywords. Keep the true `source_type` in the catalog.
   - **Background Tagging Invariant**: Never include "transparent", "transparent background", or "transparency" tags or titles on JPEG images, because JPEG files are composited on solid white (or solid colored) backgrounds. Use "white background" or "isolated on white background" for JPEGs. Reserve "transparent background" and "transparent" exclusively for RGBA transparent PNG assets.
   - Run `export_stock_metadata.py` for the eligible platform, then `embed_stock_metadata.py` on the **final color-prepared images** to write XMP title, description and keywords into copies. It verifies XMP readback and pixel identity. Check CSV structure, XMP, spelling, categories and keyword order programmatically. Re-run embedding if an image is re-exported after metadata was added.
11. **Prepare delivery.** Copy the exact platform files into dedicated delivery packages under `staging/<set>/packages/`:
   - Keep image delivery packages (`adobe_stock/`, `white_jpeg_companion/`) strictly 100% image-only (zero JSON or CSV files) to facilitate seamless drag-and-drop batch upload directly into stock portals.
   - Put all manifests, CSV spreadsheets (`adobe_stock.csv`), catalogs (`catalog.json`), and the labeled contact sheet (`contact_sheet_4k.jpg`) in a dedicated `metadata/` package with `package_purpose: "metadata_companion"`.
   - Do not generate redundant white-background PNG companions unless specifically requested; provide 1 transparent PNG folder and 1 solid-white JPEG folder. For Adobe AI work, record that the Contributor Portal **Created using generative AI tools** checkbox must be selected at submission.
12. **Manifest and audit.** Add `submission_manifest.json` to each internal package without an image-review `status` or `visual_review` field, with actual platform/source type, truthful technical/metadata/rights checks, and every package file in `assets`. Run `python scripts/package_stock_set.py --set-id <set-id> --packages <platform-package> [<companion-package>]` to create one `output/<set-id>/` folder with `set_manifest.json` listing all internal packages, then run `python scripts/audit_output.py` and deliver that folder. Do not split a single request into multiple top-level output folders or create ZIP delivery. Audit validates safe paths, package structure and declared checks, not visual quality or platform acceptance.
   - **Submission Checklist & GitHub Tracking**: Finalizing packaging automatically runs `scripts/update_submission_checklist.py` to record the new set into `docs/projects.json` and generate the interactive checklist web app in `docs/index.html` (with persistent browser `localStorage` tracking for Adobe Stock, Shutterstock, 123RF, and other platforms). Pass `--push` to auto-commit and deploy to GitHub Pages (`https://armwoottipong.github.io/Stock_automation/`).

Progress updates may report intermediate counts and paths, but keep executing through Step 12 before concluding. Report the prepared count, output path, audit result, and checklist URL. The 2026-09-26 fruit set is an example of an audited production package.

## 4. Multi-image request

For a request such as five genuinely different apples, define five descriptions/seeds and plan a generation batch. The batch runner executes one operation per item; it does **not** chain generation → upscale → cutout → metadata. After structural QC, create another batch using the valid generation output paths for 4× upscale, then another using the enlarged paths for opaque cutout. Each later batch must be newly frozen because its inputs are newly produced files. Example manifest shape:

```json
{
  "schema_version": 1,
  "max_attempts": 2,
  "items": [
    {"id": "apple_whole", "request": {"operation": "generate", "description": "whole ripe red apple", "seed": 1001}},
    {"id": "apple_halved", "request": {"operation": "generate", "description": "red apple cut in half with visible seeds", "seed": 1002}}
  ]
}
```

```powershell
python scripts\batch.py plan --manifest staging\apple_set\generation_batch.json
python scripts\batch.py run --plan jobs\batches\BATCH_ID\batch_plan.json
python scripts\batch.py status --plan jobs\batches\BATCH_ID\batch_plan.json
```

Replace `BATCH_ID` with the ID printed by `plan`; do not copy a placeholder into a real command. `report.json` gives status/counts, attempts, execution seconds and output bytes. `completed` means deterministic execution finished. A structural count shortfall means generate more candidates before delivery. Prepare color, metadata and the exact output package, then audit it. The user may cull files afterward. See `docs/phase-9-results.md` and `.agents/skills/run-stock-batch/SKILL.md` for resume and retry behavior.

## 5. System or model update sequence

An update is a separate experiment, never a silent change to an existing frozen job. Scope the update (dependency, checkpoint, ComfyUI, custom node or code), save the current version and `git status`, and run baseline tests and a representative smoke job. Before **model** research, read the six `data/*registry.json` files plus `data/research_cache.json`. Check the publisher's official source/license, verification date, commercial terms, checkpoint hash, version compatibility, disk space and 8 GB VRAM fit. Do not download or install until these checks are recorded in a plan and the action is authorized. Record installations in the relevant registry.

Freeze comparison inputs and preprocessing under `benchmarks/`, run incumbent and candidate on the same representative white/solid Isolate cases, capture output, errors, timing and peak memory, and inspect full-size geometry, fine edges, retained background and source shadow/reflection. Keep transparent materials as a separate manual case. The current background benchmark tools support **only** registered `birefnet-dis` and `ben2-base`:

```powershell
.\.venv-comfyui\Scripts\python.exe scripts\benchmark_background.py --manifest isolated_cases.json --model birefnet-dis
.\.venv-comfyui\Scripts\python.exe scripts\benchmark_background.py --manifest isolated_cases.json --model ben2-base
.\.venv-comfyui\Scripts\python.exe scripts\review_background_benchmark.py --manifest isolated_cases.json
```

Their outputs are under `benchmarks/background/output/`. A new candidate requires a verified adapter/registry change first; do not pass an unregistered name to this script. For an upscale/system update, put representative same-input comparisons, timings, failure notes and visual sheets under a dated `benchmarks/<topic>/<date>/` directory. Record findings and limitations in a tracked `docs/` result, update registry and reviewed research cache only if evidence supports the new choice, then replan affected jobs. Run `python -m pytest -q`, `python scripts/audit_output.py` and a smoke job for changed execution paths. Check that the change did not place experiments in `output/`; update the relevant skill only for a tested workflow. See `.agents/skills/compare-models/SKILL.md` and `.agents/skills/research-cache/SKILL.md`.

## 6. Recovery and handoff

- If `plan` says research is stale/invalid, stop that route, review official evidence and local benchmarks, update registries/cache, then make a new plan. Never bypass the gate or reuse an old plan after its evidence changes.
- If ComfyUI disconnects or a GPU attempt fails, inspect the saved job and batch checkpoints. Restart the server and rerun the same frozen plan to resume. Use batch `--retry-failed` only after the cause is corrected. Do not delete checkpoints to force success.
- If a source image or workflow/model file changed, create a new plan. Hash mismatch is an intentional safety gate.
- If an image fails deterministic technical, metadata or rights checks, keep it in staging with a failure note; regenerate or correct it. Package every structurally valid item.
- Before handoff to another agent, provide the checkout path, Git commit, local runtime/model availability, plan/batch IDs, artifact paths, counts and exact pending human decisions. Worktree clones lack ignored weights and image data.
