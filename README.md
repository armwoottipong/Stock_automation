# AI Image Automation

Local Python controller and ComfyUI project targeting an RTX 4060 with 8 GB VRAM. The project is being built in phases. **Phase 1 foundation is implemented; image jobs are not runnable yet.**

## Current state

- Windows 11 Pro; Python 3.12.6; RTX 4060 (8188 MiB), NVIDIA driver 591.86.
- The active global Python has CPU-only PyTorch 2.10.0. A separate CUDA environment is needed for ComfyUI.
- No ComfyUI installation or API listener was found during the initial inspection.
- Model, license, tool, and research registries start empty. No model has been verified or selected.

## Phase 1 commands

```powershell
cd D:\Stock_automation
python -m pip install -e '.[dev]'
python -m pytest -q
python -c "from ai_image_automation.config import load_settings; print(load_settings().model_dump_json(indent=2))"
```

`config/default.yaml` is the baseline configuration. `config/hardware_8gb.yaml` records the hardware profile. Settings are validated by Pydantic; registry files are validated by the models in `src/ai_image_automation/registry.py`. Runtime logs use JSON Lines.

See [implementation plan](docs/implementation-plan.md) for the remaining phases. CLI commands, ComfyUI workflows, model selection, background removal, and batch rendering arrive in later phases.
