# Phase 6 opaque-object background removal — 2026-09-25

## Implemented path

`scripts/remove_background.py` runs BiRefNet standard DIS in `.venv-comfyui` as a separate Python process. It does not call an LLM or alter the ComfyUI render loop. The request requires an explicit subject type. Only `opaque` runs inference; `glass` and `translucent` produce a review record with no cutout. The checkpoint must match the installed model's SHA-256 and a commercially allowed registry/license pair.

Before inference the script freezes input path/hash, model revision/hash, alpha thresholds, source dimensions and clean-cutout policy under `jobs/<job_id>/request.json`. Repeat calls reuse an unchanged output by hash. The result is a transparent PNG and `qc.json`; `manual_review_required` remains the status even when structural QC passes.

The opaque matte refinement clips very low alpha to transparent and very high alpha to opaque, leaving intermediate edge pixels intact. It does not erode or reshape the subject. QC checks unchanged dimensions and RGB pixels, nonempty foreground, transparent background, object bounds and alpha range. Corner samples report whether an input appears near white or simple solid; this is a diagnostic, not a whole-image proof. Visual review must verify geometry, edge halos, original shadow and floor reflection removal, and absence of text, logos and branding. No automated test can certify these visual properties yet.

## Local smoke checks

| Input | Result |
| --- | --- |
| Phase 5 Isolate ceramic mug on a gray studio gradient | 1024 × 1024 transparent PNG; body and handle retained; structural QC passed; background review flagged the gradient. |
| Phase 5 perfume bottle with floor shadow/reflection | 1024 × 1024 transparent PNG; bottle retained and floor shadow/reflection absent on checkerboard review; structural QC passed. The bottle includes glass-like material, so interior transparency still needs human review. |
| Clear glass fixture with `--subject glass` | No cutout; review record created. |
| White-background technical smoke made by compositing the mug cutout onto pure white | Input classified `near_white: true`; BiRefNet returned a cutout with structural QC passed. This derived image is not an independent white-background accuracy benchmark. |

Peak PyTorch allocated memory was 1.584 GiB for each opaque smoke run on the RTX 4060. The script runs independently of the ComfyUI server and uses the pinned Phase 5 publisher code and verified safetensors already installed. No additional model or custom node was downloaded.

## Use

```powershell
.\.venv-comfyui\Scripts\python.exe scripts\remove_background.py --input path\to\object.png --subject opaque
```

The command prints its job ID and output path. Inspect the transparent PNG over both white and dark/checkerboard backgrounds and review `jobs/<job_id>/qc.json` before using it. A successful command means a cutout was made, **not** that it is approved for photostock. For glass or sheer material, pass `--subject glass` or `--subject translucent` to record the required manual route.

## Remaining limits

There is no reliable automatic segmentation of glass or sheer material, no color decontamination for transparent interiors, and no automatic OCR/logo or visual shadow guarantee. The tested SDXL generation workflow still often makes gray gradients despite pure-white prompts. Phase 7 can cache research, but production stock submission remains gated on human visual review and further input-generation quality work.
