# Phase 3 results — 2026-09-25

- Checkpoint: official SDXL Base 1.0, 6,938,078,334 bytes; SHA-256 matched the official file page.
- Hardware: RTX 4060 with 8188 MiB VRAM, ComfyUI 0.37.0, PyTorch 2.14.0+cu130, `--lowvram`.
- Workflow: 1024×1024, 26 steps, CFG 5.0, `dpmpp_2m` + `karras`, seed 42.
- Job: `f217d9f361e42991`; output: `jobs/f217d9f361e42991/output/image_001.png`.
- ComfyUI reported 24.18 seconds execution. `nvidia-smi` showed about 7104 MiB used during sampling; this is one observation, not a worst-case bound.
- Script QC: passed integrity, dimensions, and nonblank checks; no reported issues.
- Visual review: the perfume bottle and reflections rendered, but the label text was illegible. This output is a functional validation image and is not approved as a final commercial product image.

Recommended next phase: implement pixel and tiled creative upscale with verified model/node sources, then compare quality and VRAM behavior on a small set of subject types. Keep label artwork as an external compositing step or explicitly review it before commercial export.
