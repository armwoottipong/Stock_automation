# AI Image Automation

Local Python controller and ComfyUI project targeting an RTX 4060 with 8 GB VRAM. The project is being built in phases. **Phases 1–9 are complete within their documented scope.**

## Current state

- Windows 11 Pro; Python 3.12.6; RTX 4060 (8188 MiB), NVIDIA driver 591.86.
- The active global Python has CPU-only PyTorch 2.10.0. ComfyUI uses a separate `.venv-comfyui` environment with CUDA-enabled PyTorch.
- The initial inspection found no ComfyUI installation. An official ComfyUI 0.37.0 checkout is now in `vendor/ComfyUI`, excluded from this repository. Its revision and license are recorded in `data/`.
- SDXL Base 1.0, RealESRGAN x2plus, xinsir SDXL ControlNet Tile, BiRefNet DIS and BEN2 Base are installed locally and registered with source and license evidence.

## Phase 1 commands

```powershell
cd D:\Stock_automation
python -m pip install -e '.[dev]'
python -m pytest -q
python -c "from ai_image_automation.config import load_settings; print(load_settings().model_dump_json(indent=2))"
```

`config/default.yaml` is the baseline configuration. `config/hardware_8gb.yaml` records the hardware profile. Settings are validated by Pydantic; registry files are validated by the models in `src/ai_image_automation/registry.py`. Runtime logs use JSON Lines.

See [implementation plan](docs/implementation-plan.md) for the remaining phases. Routing and batch rendering arrive in later phases.

The controller can also be operated from another coding agent or IDE; see [agent usage](docs/agent-usage.md) for workspace and Git worktree notes.

## Phase 2 API commands

Start ComfyUI in one PowerShell terminal:

```powershell
cd D:\Stock_automation
.\scripts\start_comfyui.ps1
```

In another terminal, check the API or submit an exported **API-format** ComfyUI workflow:

```powershell
python controller.py health
python controller.py submit --workflow path\to\workflow_api.json
python controller.py resume JOB_ID
```

Submitted workflows are saved under `jobs/<job_id>/` with a status checkpoint. Repeating the same workflow resumes a queued job or returns a completed job without queueing it again. These commands require a running ComfyUI server. No checkpoint model is bundled with this repository.

To smoke-test the API without a model, submit `workflows/templates/api_smoke_empty_image.json`; it produces a 64×64 PNG.

## Phase 3 generation

The `generate` command uses the registered SDXL checkpoint and checks its commercial license record by default. The approved checkpoint is installed locally; see the [research comparison](docs/model-research-2026-09-25.md), [install record](docs/model-install-plan.md), and [Phase 3 results](docs/phase-3-results.md).

Start ComfyUI, then run:

```powershell
cd D:\Stock_automation
python controller.py generate --prompt "premium perfume bottle, studio product photography" --model-id sdxl-base-1.0 --seed 42
```

The controller freezes the API workflow in `jobs/<job_id>/workflow.json`, records the request and prompt, and writes deterministic image checks to `jobs/<job_id>/qc.json`. The current checks cover integrity, dimensions and blank output; they do not score artistic or photographic quality. QC also records a required manual review for visible text, logos and branding.

Stock images must contain no visible text, logos, trademarks, labels or branding. Generation and creative upscale add these to the negative prompt, but the initial perfume bottle test still produced illegible label-like text. Reject or regenerate any suspect image during final review; structural QC does not clear it for submission.

## Phase 4 upscale preparation

The `upscale` command stages an existing image in ComfyUI's input folder, runs a 2× model-backed pixel workflow, and checks output dimensions. `creative-upscale` prepares a guided-filter control image and uses SDXL ControlNet Tile with Ultimate SD Upscale, Half Tile seam fix, and tiled VAE decode. Both commands check registered licenses for commercial jobs and save request, workflow, and QC files under `jobs/<job_id>/`.

The [Phase 4 installation record](docs/phase-4-install-plan.md) gives model sources, licenses and hashes. See [Phase 4 results](docs/phase-4-results.md) for live timings and quality limits. With ComfyUI running, use:

```powershell
python controller.py upscale --input jobs\f217d9f361e42991\output\image_001.png
python controller.py creative-upscale --input path\to\pixel_output.png --prompt "refine glass reflections and fine edges without changing bottle shape"
```

The initial product example reached 2048×2048 and passed structural QC in both modes. Creative refinement took about five minutes. Generated label-like text remained visible, so that image does not pass stock-content review.

## Phase 5 background research

The [Phase 5 comparison](docs/phase-5-results.md) uses seven locally generated Isolate objects as its primary benchmark. BiRefNet is the provisional choice for opaque objects; glass and sheer fabric require a review path. The generated fixtures have simple gray studio backgrounds despite white prompts, so the generation stage still needs a white-background acceptance check.

## Phase 6 background removal

The [Phase 6 workflow](docs/phase-6-results.md) can cut out an opaque isolated object with the registered BiRefNet model. Run it from the repository root with the CUDA Python environment:

```powershell
.\.venv-comfyui\Scripts\python.exe scripts\remove_background.py --input path\to\object.png --subject opaque
```

The command writes a transparent PNG and QC under `jobs/<job_id>/`. Glass and sheer subjects route to manual review without an automatic cutout. All results still require visual review for geometry, edge quality, original shadow/reflection and any text or branding before photostock submission.

## Phase 7 research cache

The [research cache](docs/phase-7-results.md) reuses reviewed model decisions without network requests during a job. It contains a provisional BiRefNet choice for opaque Isolate objects, manual routes for glass/sheer objects, and the tested 2× pixel upscaler. Check a decision with:

```powershell
python scripts\research_cache.py lookup --task remove_background --subject opaque_isolate
```

Expired or registry-invalid entries provide no usable model ID. Updating an entry requires a reviewed JSON record and matching registry/license verification dates.

## Phase 8 job router

The [router](docs/phase-8-results.md) accepts a structured JSON request, selects a reviewed workflow, and freezes model, input and prompt settings before execution:

```powershell
python scripts\router.py plan --request path\to\request.json
python scripts\router.py run --plan jobs\PLAN_ID\plan.json
```

Supported operations are isolated-object generation, pixel 2× upscale, creative product upscale and background removal. Transparent subjects route to manual review. An execution result marked `completed_requires_review` is still subject to visual stock checks.

## Phase 9 batch jobs

The [batch runner](docs/phase-9-results.md) freezes every item decision in one batch plan, then executes sequentially with file checkpoints and progress reports. Create a JSON manifest as shown in the Phase 9 results, then run:

```powershell
python scripts\batch.py plan --manifest path\to\batch.json
python scripts\batch.py run --plan jobs\batches\BATCH_ID\batch_plan.json
python scripts\batch.py status --plan jobs\batches\BATCH_ID\batch_plan.json
```

Running the same plan again resumes pending work and skips completed files. Transient failures have bounded automatic retries; deterministic failures are recorded while later files continue. Every output still requires visual review for photostock.

## Phase 10 hardening

The [hardening results](docs/phase-10-results.md) cover checkpoint recovery, batch metrics, security review and an offline integration test. `report.json` now includes total attempts, execution seconds and output bytes. Execution seconds are `null` for batches created before these metrics were added.

Inspect free disk space and stale atomic-write files without deleting anything:

```powershell
python scripts\maintenance.py
```

After checking the preview, `python scripts\maintenance.py --apply` removes only `*.tmp` files older than seven days within `jobs/`. It never removes image outputs, models, source images or batch checkpoints. Change the age with `--older-than-days N` (minimum 1). Keep human review in the stock submission workflow, especially for text, logos, trademarks, branding, object geometry and cutout edges.
