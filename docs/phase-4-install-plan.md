# Phase 4 upscale installation record — 2026-09-25

**Status:** approved, installed, and smoke-tested. See [Phase 4 results](phase-4-results.md).

## Intended result

Upscale an existing image with a model-backed pixel pass, optionally refine it with an SDXL tile diffusion pass, and check output dimensions and image integrity. Use the existing ComfyUI server, 8 GB low-VRAM mode, and registered SDXL Base checkpoint. A pixel-only path remains usable when creative refinement cannot fit in VRAM.

## Proposed downloads

| Resource | Publisher source and license | Size | Install location | Role |
| --- | --- | ---: | --- | --- |
| `RealESRGAN_x2plus.pth` | [Official Real-ESRGAN v0.2.1 release](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.2.1), [BSD-3-Clause license](https://github.com/xinntao/Real-ESRGAN/blob/master/LICENSE) | 67,061,725 bytes | `vendor/ComfyUI/models/upscale_models/` | 2× pixel upscale |
| `diffusion_pytorch_model.safetensors` from xinsir Tile SDXL | [Publisher model card](https://huggingface.co/xinsir/controlnet-tile-sdxl-1.0), [publisher file](https://huggingface.co/xinsir/controlnet-tile-sdxl-1.0/blob/1ae8d9529efe58f7362a987363ff86a7904dc84f/diffusion_pytorch_model.safetensors), Apache-2.0 shown on card | about 2.5 GB | `vendor/ComfyUI/models/controlnet/xinsir-controlnet-tile-sdxl-1.0.safetensors` | structure guidance for creative tiles |
| `ComfyUI_UltimateSDUpscale` custom node | [Maintainer repository](https://github.com/ssitu/ComfyUI_UltimateSDUpscale) at `a5547db9e1d07d3318bb21e9e9c474f4c1e9c8df`, [GPL-3.0 license](https://github.com/ssitu/ComfyUI_UltimateSDUpscale/blob/main/LICENSE) | source checkout | `vendor/ComfyUI/custom_nodes/ComfyUI_UltimateSDUpscale/` | tile redraw, Half Tile seam fix and tiled VAE decode |

The two model downloads were approved after this plan was prepared. On this machine, drive D had about 94.8 GB free at planning time. The downloaded model files and node checkout stay outside Git. `RealESRGAN_x2plus.pth` measured 67,061,725 bytes, matching its official release asset size, and local SHA-256 was `49fafd45f8fd7aa8d31ab2a22d14d91b536c34494a5cfe31eb5d89c2fa266abb`. The publisher page gives SHA-256 `9f23ba7be22bf8796c12565e00ea4b287acac982cdf384d368a8b18b6990e011` for ControlNet; the downloaded 2,502,139,104-byte file matched.

The Ultimate SD Upscale node is installed at the pinned revision. Its `ultimate_sd_upscale` submodule is pinned at `2322caa480535b1011a1f9c18126d85ea444f146`; this avoids the node's unpinned runtime fallback download. ComfyUI loaded `UltimateSDUpscaleNoUpscale` successfully after restart, and the workflow template's inputs match the node schema.

The node's `tiled_decode` path calls ComfyUI's `VAEDecodeTiled` with tile size 512. The installed ComfyUI node defaults overlap to 64, matching the setup document's baseline.

## Execution and fallback

1. Build and test pixel workflow planning and input handling without downloading models.
2. After approval, install and verify the two files and the pinned custom node, then restart ComfyUI and check its node schemas.
3. Smoke-test 2× pixel upscale on the Phase 3 image; check dimensions, integrity and VRAM.
4. Prepare a guided-filter control image. Run tiled creative refinement with conservative denoise, ControlNet start/end, Half Tile seam fix and tiled decode. If 8 GB is insufficient, reduce tile size and retry as a separate immutable job; record the successful or failed settings.
5. Review subject geometry, seams and label text visually. A successful script QC is not a guarantee of commercially usable detail.

The suggested portrait and architecture upscalers from the setup document remain research candidates. This first implementation uses an official, lower-memory 2× general model to establish a working path. Subject-specific comparison can follow after the baseline works.
