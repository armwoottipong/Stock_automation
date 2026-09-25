---
name: upscale
description: Upscale an image with this project's registered ComfyUI pixel or creative workflow, while checking model licenses, dimensions and stock-content review. Use for existing images; not for background removal.
---

# Upscale a project image

Work from the repository root. Use `controller.py` and the registered models; inspect `docs/phase-4-results.md` for the tested setup and limits. Verify ComfyUI health and the relevant `data/upscaler_registry.json`, `data/model_registry.json`, `data/controlnet_registry.json` and `data/license_registry.json` entries before running a commercial job. Do not install a new checkpoint or node without the source, license, compatibility, disk and provenance checks in `AGENTS.md`.

For faithful 2× enlargement, run `python controller.py upscale --input <image>`. Use `python controller.py creative-upscale --input <image> --prompt <requested refinement>` only when the user wants generative changes; it can alter contours and reflections. Both workflows save frozen job settings and QC under `jobs/<job_id>/`. Review those files and compare the result to the input for geometry, seams and artifacts. The creative workflow's tested low-VRAM retry is built into the controller.

Every stock result also needs visual review for visible text, logos, trademarks, labels and branding. Reject or regenerate suspect output. Structural QC success alone does not approve an image for photostock.
