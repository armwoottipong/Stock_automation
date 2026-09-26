# Agent runbook: from request to stock package

Last reviewed: 2026-09-26. This is the entry point for an agent operating the **existing** local pipeline. Read `AGENTS.md` first, then this file, `docs/implementation-plan.md`, `docs/artifact-lifecycle.md`, and the relevant `.agents/skills/<name>/SKILL.md`. The repository implements Phases 1–10 within their documented limits. A phase marked complete does not mean an image is approved by a stock platform.

## 1. Operating contract

The project makes unbranded, isolated objects, preferably on a white or simple solid background. Production image requests should be carried from brief to a reviewed, platform-specific package when all gates pass. A request for 25 images means 25 distinct **approved** images, not merely 25 renders. If any mandatory review or rights evidence is missing, keep the affected files in `staging/`, report the exact blocker, and leave `output/` clean. Never set a manifest check to `true` just to make the audit pass.

Planning and execution are separate. An agent may interpret the brief, check research and policy, create structured JSON, and inspect results. `router.py plan` or `batch.py plan` freezes model choices, prompt, source hashes and workflow settings. `run` then executes the frozen plan through Python/ComfyUI without an LLM or web call in the render loop. Editing source files, checkpoints, registries or research after planning requires a **new** plan. Keep one GPU job at a time on the RTX 4060 8 GB machine.

The current route choices are narrow:

| Operation | Current implementation | Important limit |
| --- | --- | --- |
| Generate isolated object | FLUX.2 Klein 4B distilled FP8 at 4 steps, CFG 1 | Provisional local winner over SDXL on four white-background cases. Inspect anatomy, edges, actual background and branding; keep drafts in staging until approved. |
| Pixel upscale | RealESRGAN x4plus at **4× by default**; explicit x2plus at 2× | 4× selection is provisional from a five-fruit comparison. Inspect invented detail and contours. |
| Creative upscale | SDXL + xinsir Tile ControlNet | May change object geometry. Use only if the brief allows creative refinement. |
| Remove opaque background | BiRefNet DIS, clean cutout without original shadow/floor reflection | Provisional opaque route; inspect alpha on white, dark and checkerboard. |
| Remove glass/translucent background | Manual-review route; no automatic cutout | Do not relabel these subjects as opaque. |

No command automatically clears visible text, logos, trademarks, branding, anatomical errors, excessive similarity, rights or stock acceptance. A structural `qc.json` pass and `completed_requires_review` are intermediate states. Reject, correct or regenerate suspect work. The metadata catalog must record true origin (`generative_ai` or `camera_photo`). Buyer-facing titles and keywords describe the subject; keep provenance in the catalog and complete any platform disclosure in its portal. As checked on 2026-09-26, [Adobe requires its generative-AI disclosure and rights review](https://helpx.adobe.com/stock/contributor/submit-your-content/submit-generative-ai-content/submit-generative-ai-content.html); [Shutterstock does not accept contributor AI-generated content](https://submit.shutterstock.com/help/en/articles/10594622-content-policy-updates-ai-generated-content). Recheck official rules immediately before submission.

## 2. Where every artifact goes

| Directory | Contents and retention |
| --- | --- |
| `input/` | User-supplied originals. Record source and rights; do not overwrite. |
| `jobs/<id>/` | Frozen single plans, requests, ComfyUI workflow, raw outputs, execution record and deterministic QC. |
| `jobs/batches/<id>/` | Frozen batch plan, per-item checkpoints, progress, report and safe event log. |
| `staging/<set>/` | Candidate images, selected drafts, review evidence, metadata catalog, XMP copies and upload preparation. |
| `staging/packages/` | Review ZIPs; a ZIP here is not a final submission. |
| `benchmarks/` | Controlled model comparisons and system-update experiments, with test inputs, outputs, runtime/VRAM and visual sheets. |
| `logs/` | Runtime diagnostics. No secrets or final deliverables. |
| `output/<platform-set>/` | Only a fully reviewed submission package with `submission_manifest.json`; no loose files. |
| `data/` | Model/tool/license registries and reviewed research cache. Model weights are local under ignored `vendor/`. |

Large local images, models, `jobs/`, `staging/` contents and benchmark outputs are Git-ignored. A fresh clone or separate worktree does **not** contain them. See `docs/agent-usage.md` before handing execution to another agent or machine.

## 3. New production job: complete sequence

1. **Intake.** Record subject, count, distinct variants, intended platform, true source type, white/solid or transparent deliverable, aspect ratio, resolution, allowed props, exclusions and commercial rights. For generated stock work, do not request text, labels, logos, trademarks or branding. For a real photo, keep truthful `camera_photo` provenance. Select a platform the source type permits.
2. **Preflight.** From the repository root, check `git status --short`, disk, Python/CUDA environment, validated settings (`python -c "from ai_image_automation.config import load_settings; print(load_settings().model_dump_json())"`), `python controller.py health`, and `python scripts/research_cache.py list`. Confirm the relevant selected entry is fresh and the local checkpoint hash/license matches its registry. The cache is evidence, not permission to ignore a platform rule. Start ComfyUI with `./scripts/start_comfyui.ps1` if needed. Use `python -m pytest -q` after a code/configuration change.
3. **Create a structured request.** For one operation use `scripts/router.py plan --request <JSON>`. For 2–1000 independent items use `scripts/batch.py plan --manifest <JSON>`. Inspect the frozen `plan.json` or `batch_plan.json`: operation, subject, prompt exclusions, model, scale, input hash, research freshness and route. Do not assume free-form text invokes upscale or cutout automatically. In a multi-step job, feed the reviewed output of one step into a **new** plan for the next step.
4. **Run and checkpoint.** Execute the saved plan, read `execution.json` and the underlying `jobs/<job_id>/qc.json`. For batches, use `status` and `report.json`. A repeat `run` resumes or reuses valid completed work. Automatic retries cover only bounded transient failures; fix deterministic failures, then use `run --retry-failed` when appropriate.
5. **Review source render.** Inspect every candidate at full size. Check actual white/solid background (not just the prompt), margins, plausible object anatomy, intact geometry, no detached pieces, no text/logo/branding, and distinctness across variants. Reject or regenerate failures. White/solid input makes cutout easier but does not guarantee it.
6. **Upscale as requested.** For the default, plan `{"operation":"upscale","input":"..."}` (4×). Inspect sharpened edges, invented texture, seams and dimension change. Choose 2× explicitly only when appropriate. Creative upscale is a separate route and needs another geometry review.
7. **Remove background when the deliverable calls for transparency.** Plan `remove_background` with `subject_type: opaque_isolate`. Inspect the resulting transparent PNG on white, dark and checkerboard at 100% or greater. Require the subject to remain complete and the original shadow/floor reflection to be gone. Glass and sheer material stop at manual review. If the deliverable is an opaque white image, preserve that image; a cutout is not automatically required.
8. **Stage and curate.** Copy chosen raw results to a named `staging/<set>/` folder, keeping provenance back to plan/job IDs. Do not move `jobs/` checkpoints. Keep only genuinely distinct approved candidates for metadata preparation; record each rejection and reason in local review notes. Check source rights, any releases, tool/model commercial terms and platform eligibility.
9. **Prepare platform file.** Confirm dimensions, file type, color space/profile, transparency or white-background specification, size and alpha quality against **current** official platform requirements. Adobe's current [transparent PNG requirements](https://helpx.adobe.com/stock/contributor/submit-your-content/submit-pngs/technical-requirements-png-submission.html) include 4–100 MP, at most 45 MB, sRGB and actual transparency. A file with no ICC profile must not be marked as color-verified solely because it looks correct. Use a color-managed editor or a reviewed conversion step, then verify the exported file. A white-background upload may need a different photo-format preparation. The project has no automatic final color conversion or portal uploader.
10. **Write and embed metadata.** Make an English catalog with exact staged filenames, accurate descriptive titles and ordered relevant keywords. Keep the true `source_type` in the catalog. Run `export_stock_metadata.py` for the eligible platform, then `embed_stock_metadata.py` on the **final color-prepared images** to write XMP title, description and keywords into copies. It verifies XMP readback and pixel identity, but reports `draft_manual_review_required`. Inspect the CSV, XMP, spelling, categories, keyword order and portal import behavior. Re-run embedding if an image is re-exported after metadata was added.
11. **Final human/technical gate.** For every selected file, record full-size visual approval, similarity selection, metadata review, rights and platform format/color checks. Check the exact upload files after all transformations. Never infer these decisions from the structural QC or XMP report. For Adobe AI work, record that the Contributor Portal **Created using generative AI tools** checkbox must be selected at submission. If any gate fails, return the file to staging/rework.
12. **Promote and audit.** Copy only the approved upload files and their platform CSV, if used, into `output/<platform-set>/`. Add a `submission_manifest.json` with `status: ready_to_submit`, actual platform/source type, all four truthful checks, and a relative inventory of every package file. Run `python scripts/audit_output.py`; it checks package structure and declared checks, **not** the truth of human review. The portal submission itself is a separate action. Record portal import checks, AI disclosure and submission result when it happens.

At the end of each requested phase, report what ran, counts accepted/rejected, paths, tests, blockers and the next step. Do not call a draft or a metadata-embedded file “final” until Step 11 is complete. `output/` currently contains no approved image package.

## 4. Executable single-image example: red apple to Adobe draft, then final

This is a command template for a **new** one-image job, run from `D:\Stock_automation` in PowerShell. It does not assert that an apple has already passed review. Inspect each returned file and stop on failure. `$LASTEXITCODE` should be checked after each Python command in automation.

```powershell
cd D:\Stock_automation
.\scripts\start_comfyui.ps1                 # keep this server terminal open
```

In a second PowerShell terminal:

```powershell
cd D:\Stock_automation
python controller.py health
python scripts\research_cache.py lookup --task generate --subject isolated_object
python scripts\research_cache.py lookup --task upscale --subject pixel_4x
python scripts\research_cache.py lookup --task remove_background --subject opaque_isolate
New-Item -ItemType Directory -Force staging\demo_red_apple | Out-Null
function Save-Json($Path, $Value) {
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText((Join-Path (Get-Location) $Path), ($Value | ConvertTo-Json -Depth 10), $utf8)
}
Save-Json 'staging\demo_red_apple\generate_request.json' @{ operation = 'generate'; description = 'ripe red apple'; seed = 618; width = 1024; height = 1024 }
$genPlan = python scripts\router.py plan --request staging\demo_red_apple\generate_request.json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Generation planning failed' }
$gen = python scripts\router.py run --plan $genPlan.plan | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $gen.status -ne 'completed_requires_review') { throw 'Generation failed' }
$source = $gen.outputs[0]
```

Open `$source` at full size. Require a usable white/simple solid Isolate source, correct apple shape and no text/branding. A gray gradient or defect means regenerate with a new seed/request before continuing. Then plan a **new** 4× step:

```powershell
Save-Json 'staging\demo_red_apple\upscale_request.json' @{ operation = 'upscale'; input = $source }
$upPlan = python scripts\router.py plan --request staging\demo_red_apple\upscale_request.json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Upscale planning failed' }
$up = python scripts\router.py run --plan $upPlan.plan | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $up.status -ne 'completed_requires_review') { throw 'Upscale failed' }
$large = $up.outputs[0]
```

Inspect `$large` at 100% for invented fruit texture and edge defects. If transparent PNG is the selected product, create another plan:

```powershell
Save-Json 'staging\demo_red_apple\cutout_request.json' @{ operation = 'remove_background'; subject_type = 'opaque_isolate'; input = $large }
$cutPlan = python scripts\router.py plan --request staging\demo_red_apple\cutout_request.json | ConvertFrom-Json
if ($LASTEXITCODE -ne 0) { throw 'Cutout planning failed' }
$cut = python scripts\router.py run --plan $cutPlan.plan | ConvertFrom-Json
if ($LASTEXITCODE -ne 0 -or $cut.status -ne 'completed_requires_review') { throw 'Cutout failed' }
$cutout = $cut.outputs[0]
New-Item -ItemType Directory -Force staging\demo_red_apple\review | Out-Null
Copy-Item -LiteralPath $source -Destination staging\demo_red_apple\review\source.png
Copy-Item -LiteralPath $large -Destination staging\demo_red_apple\review\upscaled.png
Copy-Item -LiteralPath $cutout -Destination staging\demo_red_apple\review\cutout.png
```

Record the generation/upscale/cutout plan IDs and human review result in `staging/demo_red_apple/review/notes.md`. Inspect the cutout over white, black and checkerboard; reject halos, lost stem/edges, retained original shadow/reflection, text or branding. Confirm rights and compare it with existing portfolio assets. Export the **selected** transparent image to sRGB PNG in a color-managed editor, preserving transparency, as `staging/demo_red_apple/ready_for_metadata/red_apple_cutout.png`; verify the export's ICC profile, 4–100 MP and ≤45 MB. A folder named `ready_for_metadata` is still staging, not final approval.

Create `staging/demo_red_apple/metadata/catalog.json` using the following exact schema, with title and keywords edited to match the **actual image**:

```json
{
  "source_type": "generative_ai",
  "language": "en",
  "review_status": "draft_manual_review_required",
  "records": [
    {
      "filename": "red_apple_cutout.png",
      "title": "Ripe red apple isolated on transparent background",
      "keywords": ["apple", "red apple", "ripe", "fruit", "single", "isolated", "transparent background", "cutout", "food", "produce"]
    }
  ]
}
```

```powershell
python scripts\export_stock_metadata.py --catalog staging\demo_red_apple\metadata\catalog.json --assets staging\demo_red_apple\ready_for_metadata --platform adobe --output staging\demo_red_apple\metadata\adobe_stock.csv
python scripts\embed_stock_metadata.py --catalog staging\demo_red_apple\metadata\catalog.json --assets staging\demo_red_apple\ready_for_metadata --output staging\demo_red_apple\metadata\embedded_draft --platform adobe
exiftool -G1 -s -XMP-dc:Title -XMP-dc:Subject -ICC_Profile:ProfileDescription staging\demo_red_apple\metadata\embedded_draft\red_apple_cutout.png
```

Check the embedded image again. The `embedded_draft` name is intentional: XMP success is not stock approval. If the final human review, format/color/profile checks, metadata, rights and platform rules all pass, copy **that exact file** and the CSV to a new output package. Create `submission_manifest.json` there with the truthful checks. Example of the required shape:

```json
{
  "status": "ready_to_submit",
  "platform": "adobe_stock",
  "source_type": "generative_ai",
  "adobe_ai_disclosure_required": true,
  "checks": {"visual_review": true, "metadata": true, "technical": true, "rights": true},
  "assets": ["red_apple_cutout.png", "adobe_stock.csv"]
}
```

The example manifest is a **template**, not evidence that the checks passed. Only write it after the reviewer records those decisions. Then run `python scripts/audit_output.py` and inspect the package. Do not put review notes, source renders or experimental files in `output/`. At Adobe submission, confirm the imported metadata/category and set the AI disclosure in the portal; do not route this AI image to Shutterstock.

After all four checks genuinely pass, the final copy and audit are:

```powershell
New-Item -ItemType Directory -Force output\adobe_red_apple | Out-Null
Copy-Item -LiteralPath staging\demo_red_apple\metadata\embedded_draft\red_apple_cutout.png -Destination output\adobe_red_apple\red_apple_cutout.png
Copy-Item -LiteralPath staging\demo_red_apple\metadata\adobe_stock.csv -Destination output\adobe_red_apple\adobe_stock.csv
Save-Json 'output\adobe_red_apple\submission_manifest.json' @{
  status = 'ready_to_submit'; platform = 'adobe_stock'; source_type = 'generative_ai'
  adobe_ai_disclosure_required = $true
  checks = @{ visual_review = $true; metadata = $true; technical = $true; rights = $true }
  assets = @('red_apple_cutout.png', 'adobe_stock.csv')
}
python scripts\audit_output.py
```

## 5. Multi-image request

For a request such as five genuinely different apples, define five descriptions/seeds and plan a generation batch. The batch runner executes one operation per item; it does **not** chain generation → upscale → cutout → metadata. After review, create another batch using the accepted generation output paths for 4× upscale, then another using the accepted enlarged paths for opaque cutout. Each later batch must be newly frozen because its inputs are newly produced files. Example manifest shape:

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

Replace `BATCH_ID` with the ID printed by `plan`; do not copy a placeholder into a real command. `report.json` gives status/counts, attempts, execution seconds and output bytes. `completed_requires_review` still needs file-by-file inspection. A count shortfall means generate more candidates. Curate similar variants before metadata and final promotion. See `docs/phase-9-results.md` and `.agents/skills/run-stock-batch/SKILL.md` for resume and retry behavior.

## 6. System or model update sequence

An update is a separate experiment, never a silent change to an existing frozen job. Scope the update (dependency, checkpoint, ComfyUI, custom node or code), save the current version and `git status`, and run baseline tests and a representative smoke job. Before **model** research, read the six `data/*registry.json` files plus `data/research_cache.json`. Check the publisher's official source/license, verification date, commercial terms, checkpoint hash, version compatibility, disk space and 8 GB VRAM fit. Do not download or install until these checks are recorded in a plan and the action is authorized. Record installations in the relevant registry.

Freeze comparison inputs and preprocessing under `benchmarks/`, run incumbent and candidate on the same representative white/solid Isolate cases, capture output, errors, timing and peak memory, and inspect full-size geometry, fine edges, retained background and source shadow/reflection. Keep transparent materials as a separate manual case. The current background benchmark tools support **only** registered `birefnet-dis` and `ben2-base`:

```powershell
.\.venv-comfyui\Scripts\python.exe scripts\benchmark_background.py --manifest isolated_cases.json --model birefnet-dis
.\.venv-comfyui\Scripts\python.exe scripts\benchmark_background.py --manifest isolated_cases.json --model ben2-base
.\.venv-comfyui\Scripts\python.exe scripts\review_background_benchmark.py --manifest isolated_cases.json
```

Their outputs are under `benchmarks/background/output/`. A new candidate requires a verified adapter/registry change first; do not pass an unregistered name to this script. For an upscale/system update, put representative same-input comparisons, timings, failure notes and visual sheets under a dated `benchmarks/<topic>/<date>/` directory. Record findings and limitations in a tracked `docs/` result, update registry and reviewed research cache only if evidence supports the new choice, then replan affected jobs. Run `python -m pytest -q`, `python scripts/audit_output.py` and a smoke job for changed execution paths. Check that the change did not place experiments in `output/`; update the relevant skill only for a tested workflow. See `.agents/skills/compare-models/SKILL.md` and `.agents/skills/research-cache/SKILL.md`.

## 7. Recovery and handoff

- If `plan` says research is stale/invalid, stop that route, review official evidence and local benchmarks, update registries/cache, then make a new plan. Never bypass the gate or reuse an old plan after its evidence changes.
- If ComfyUI disconnects or a GPU attempt fails, inspect the saved job and batch checkpoints. Restart the server and rerun the same frozen plan to resume. Use batch `--retry-failed` only after the cause is corrected. Do not delete checkpoints to force success.
- If a source image or workflow/model file changed, create a new plan. Hash mismatch is an intentional safety gate.
- If an image fails visual, technical, metadata or rights review, keep it in staging with a rejection note; regenerate or correct it. Do not promote the whole batch merely because some items passed.
- Before handoff to another agent, provide the checkout path, Git commit, local runtime/model availability, plan/batch IDs, artifact paths, counts and exact pending human decisions. Worktree clones lack ignored weights and image data.
