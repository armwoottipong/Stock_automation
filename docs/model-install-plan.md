# SDXL Base 1.0 install plan

**Status:** approved, installed and smoke-tested. The local file measured 6,938,078,334 bytes and SHA-256 matched the published value on 2026-09-25. The 1024 px generation run completed; see [Phase 3 results](phase-3-results.md).

- Source: official Stability AI Hugging Face repository, pinned revision `462165984030d82259a11f4367a4eed129e94a7b`.
- File: `sd_xl_base_1.0.safetensors`, 6.94 GB.
- Destination: `D:\Stock_automation\vendor\ComfyUI\models\checkpoints\sd_xl_base_1.0.safetensors` (ignored by Git).
- Expected SHA-256: `31e35c80fc4829d14f90153f4c74cd59c90b779f6afe05a74cd6120b893f7e5b`.
- Disk available before download: approximately 94.7 GiB. Model weights will remain local and will not be pushed to GitHub.
- License: CreativeML Open RAIL++-M. It permits ordinary commercial image creation subject to the published use restrictions; distributing the model has additional obligations. See [license](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/462165984030d82259a11f4367a4eed129e94a7b/LICENSE.md).

After approval:

1. Download only this file from the pinned official repository using the installed `huggingface_hub` package.
2. Compute SHA-256 locally and compare with the published hash. Do not register the model if it differs.
3. Set `installed: true` in `data/model_registry.json` only after checksum validation.
4. Start ComfyUI with `scripts/start_comfyui.ps1` and run one 1024×1024, 26-step, CFG 5.0 `dpmpp_2m` + `karras` generation through `python controller.py generate`.
5. Confirm output PNG integrity, dimensions, nonblank content, runtime and actual GPU memory behavior. Record any OOM or necessary lower-memory parameters before considering Phase 3 complete.
