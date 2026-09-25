# Environment inspection — 2026-09-25

| Item | Finding |
| --- | --- |
| OS | Windows 11 Pro, build 26200 |
| GPU | NVIDIA GeForce RTX 4060, 8188 MiB VRAM |
| Driver | NVIDIA 591.86 |
| Python | 3.12.6 |
| PyTorch in global Python | 2.10.0+cpu; `torch.cuda.is_available()` is false |
| CUDA toolkit | `nvcc` was not on PATH |
| ComfyUI | No installation in checked common paths, no running process, and no listener on port 8188 |
| Existing models, custom nodes, workflows | None inside this previously empty workspace; no external ComfyUI installation was found in checked common paths |
| Free disk space on D: | About 99 GiB at inspection |

Inspection covered the workspace, D: top-level directories, and common installation directories under C:\Users\user. It was not an exhaustive scan of every drive. An official ComfyUI clone from `https://github.com/Comfy-Org/ComfyUI.git` was attempted but failed because github.com was unreachable from the shell. No third-party mirror was substituted.

Before Phase 2, install ComfyUI into an isolated environment with a CUDA-enabled PyTorch build, then verify GPU detection and API health. The global CPU-only PyTorch installation is left untouched.

## Phase 2 update

Network access recovered. ComfyUI was cloned from the official repository at commit `88ab4a06566454ad89db8f0bedb970d6c08cd1b7` (version 0.37.0). A separate `.venv-comfyui` contains PyTorch 2.14.0+cu130 and the ComfyUI requirements. PyTorch reported `torch.cuda.is_available() == True` and `NVIDIA GeForce RTX 4060`. ComfyUI started with `--lowvram` on `127.0.0.1:8188`; `python controller.py health` reported a CUDA device. The API smoke workflow completed and produced a valid 64×64 PNG. No diffusion checkpoint or custom node was installed.
