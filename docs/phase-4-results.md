# Phase 4 results — 2026-09-25

- Hardware: RTX 4060, 8188 MiB VRAM, ComfyUI 0.37.0 in `--lowvram` mode.
- Pixel: `RealESRGAN_x2plus.pth` enlarged the Phase 3 perfume image from 1024×1024 to 2048×2048. Job `22bce387788729c6`; ComfyUI reported 2.93 seconds. Script QC passed integrity, dimensions and nonblank checks.
- Creative: SDXL Base 1.0 plus xinsir ControlNet Tile, guided filter, Ultimate SD Upscale, Half Tile seam fix, and tiled VAE decode processed the 2048×2048 pixel output. Job `08f70596c72f6171`; 26 steps, tile 768, padding 64, denoise 0.34, ControlNet strength 0.88 through step fraction 0.75. ComfyUI reported 288.97 seconds, including 21 tiles; about 6.8 GB GPU memory was observed during sampling. Script QC passed.
- The automatic retry path is covered by a test that simulates CUDA OOM and retries once with tile 512 and smaller padding. The live smoke did not need the retry.
- Visual review: the bottle remained recognizable and no prominent tile seam was visible at full-image review size. Glass reflections and some contours changed during creative refinement. The source's illegible label text remained illegible after both passes. Neither result is approved as final commercial artwork.
- Limits: this is one product image; portrait and architecture/landscape quality and worst-case VRAM are not established. Script QC does not score perceptual quality, text accuracy or geometry preservation.

Recommended next phase: research background removal candidates and benchmark 1–3 images per subject category, with license, 8 GB fit, Windows/CUDA and ComfyUI/Python compatibility checked before choosing a default.
