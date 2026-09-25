# AI Image Automation

Local Python controller and ComfyUI project targeting an RTX 4060 with 8 GB VRAM. The project is being built in phases. **Phases 1–3 are complete. SDXL Base 1.0 is installed locally and has passed one 1024 px low-VRAM generation smoke test.**

## Current state

- Windows 11 Pro; Python 3.12.6; RTX 4060 (8188 MiB), NVIDIA driver 591.86.
- The active global Python has CPU-only PyTorch 2.10.0. ComfyUI uses a separate `.venv-comfyui` environment with CUDA-enabled PyTorch.
- The initial inspection found no ComfyUI installation. An official ComfyUI 0.37.0 checkout is now in `vendor/ComfyUI`, excluded from this repository. Its revision and license are recorded in `data/`.
- SDXL Base 1.0 is registered with source, license and SHA-256. Upscale and background model registries remain empty.

## Phase 1 commands

```powershell
cd D:\Stock_automation
python -m pip install -e '.[dev]'
python -m pytest -q
python -c "from ai_image_automation.config import load_settings; print(load_settings().model_dump_json(indent=2))"
```

`config/default.yaml` is the baseline configuration. `config/hardware_8gb.yaml` records the hardware profile. Settings are validated by Pydantic; registry files are validated by the models in `src/ai_image_automation/registry.py`. Runtime logs use JSON Lines.

See [implementation plan](docs/implementation-plan.md) for the remaining phases. Generation and upscale CLI commands, production workflows, model selection, background removal, and batch rendering arrive in later phases.

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

The controller freezes the API workflow in `jobs/<job_id>/workflow.json`, records the request and prompt, and writes deterministic image checks to `jobs/<job_id>/qc.json`. The current checks cover integrity, dimensions and blank output; they do not score artistic or photographic quality.

The initial perfume bottle test generated illegible label text despite the negative prompt. Review any text-heavy commercial output manually or use a workflow that applies real label artwork separately.
