# AI Image Automation

Local Python controller and ComfyUI project targeting an RTX 4060 with 8 GB VRAM. The project is being built in phases. **Phases 1–2 are complete; Phase 3 generation code is ready for a checkpoint and live validation. No image model is installed yet.**

## Current state

- Windows 11 Pro; Python 3.12.6; RTX 4060 (8188 MiB), NVIDIA driver 591.86.
- The active global Python has CPU-only PyTorch 2.10.0. ComfyUI uses a separate `.venv-comfyui` environment with CUDA-enabled PyTorch.
- The initial inspection found no ComfyUI installation. An official ComfyUI 0.37.0 checkout is now in `vendor/ComfyUI`, excluded from this repository. Its revision and license are recorded in `data/`.
- Model, license, tool, and research registries start empty. No model has been verified or selected.

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

The `generate` command uses the registered SDXL checkpoint and checks its commercial license record by default. It currently exits with `Model sdxl-base-1.0 is not installed`, because the checkpoint download requires separate approval under the project requirements. See the [research comparison](docs/model-research-2026-09-25.md) and [install plan](docs/model-install-plan.md).

After the checkpoint is installed and verified, start ComfyUI, then run:

```powershell
cd D:\Stock_automation
python controller.py generate --prompt "premium perfume bottle, studio product photography" --model-id sdxl-base-1.0 --seed 42
```

The controller freezes the API workflow in `jobs/<job_id>/workflow.json`, records the request and prompt, and writes deterministic image checks to `jobs/<job_id>/qc.json`. The current checks cover integrity, dimensions and blank output; they do not score artistic or photographic quality.
