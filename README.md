# AI Image Automation

Local Python controller and ComfyUI project targeting an RTX 4060 with 8 GB VRAM. The project is being built in phases. **Phases 1–4 are complete. Generation and pixel/creative upscale have passed local smoke tests.**

## Current state

- Windows 11 Pro; Python 3.12.6; RTX 4060 (8188 MiB), NVIDIA driver 591.86.
- The active global Python has CPU-only PyTorch 2.10.0. ComfyUI uses a separate `.venv-comfyui` environment with CUDA-enabled PyTorch.
- The initial inspection found no ComfyUI installation. An official ComfyUI 0.37.0 checkout is now in `vendor/ComfyUI`, excluded from this repository. Its revision and license are recorded in `data/`.
- SDXL Base 1.0, RealESRGAN x2plus, and xinsir SDXL ControlNet Tile are installed locally and registered with source and license evidence. Background model registry remains empty.

## Phase 1 commands

```powershell
cd D:\Stock_automation
python -m pip install -e '.[dev]'
python -m pytest -q
python -c "from ai_image_automation.config import load_settings; print(load_settings().model_dump_json(indent=2))"
```

`config/default.yaml` is the baseline configuration. `config/hardware_8gb.yaml` records the hardware profile. Settings are validated by Pydantic; registry files are validated by the models in `src/ai_image_automation/registry.py`. Runtime logs use JSON Lines.

See [implementation plan](docs/implementation-plan.md) for the remaining phases. Background removal, routing, and batch rendering arrive in later phases.

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
