# Model inventory

Generated from the installed registries plus explicit reviewed decisions with `python scripts/build_benchmark_catalog.py`. Component cards are kept separate from standalone models.

| Model | Role | Decision |
| --- | --- | --- |
| [ben2-base](ben2-base/README.md) | Remove background | Compared alternative |
| [birefnet-dis](birefnet-dis/README.md) | Remove background | Default for opaque isolates |
| [bria-rmbg-2.0](bria-rmbg-2.0/README.md) | Remove background | Excluded: commercial license restriction |
| [flux2-klein-4b-fp8](flux2-klein-4b-fp8/README.md) | Generate | Default, provisional |
| [flux2-klein-qwen3-4b-fp4](flux2-klein-qwen3-4b-fp4/README.md) | Klein text encoder | Required component |
| [flux2-klein-vae](flux2-klein-vae/README.md) | Klein VAE | Required component |
| [realesrgan-x2plus](realesrgan-x2plus/README.md) | Pixel upscale | Explicit 2× option |
| [realesrgan-x4plus](realesrgan-x4plus/README.md) | Pixel upscale | Default 4×, provisional |
| [sdxl-base-1.0](sdxl-base-1.0/README.md) | Generate / creative upscale | Generation fallback; creative component |
| [xinsir-tile-sdxl-1.0](xinsir-tile-sdxl-1.0/README.md) | Creative upscale | Registered component |
