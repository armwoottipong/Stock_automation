# 4× fruit upscale evaluation — 2026-09-26

## Decision

Default pixel upscale is **4× from the input image**, using the official **RealESRGAN x4plus** model in one ComfyUI pass. This is a provisional choice for opaque isolated fruit on white or simple backgrounds, not a general photostock approval. The CLI retains `--scale 2 --model-id realesrgan-x2plus` for users who explicitly need 2×. Creative SDXL upscale remains a separate operation because it can alter content.

## Provenance and hardware

The x4plus checkpoint came from the [publisher's v0.1.0 release](https://github.com/xinntao/Real-ESRGAN/releases/tag/v0.1.0) on 2026-09-26: 67,040,989 bytes, SHA-256 `4fa0d38905f75ac06eb49a7951b426670021be3018265fd191d2125df9d682f1`. The [publisher's BSD-3-Clause license](https://github.com/xinntao/Real-ESRGAN/blob/master/LICENSE) permits commercial use. The checkpoint is registered in `data/upscaler_registry.json` and matching license evidence in `data/license_registry.json`. There was more than 88 GB free disk space before download. ComfyUI's [ImageUpscaleWithModel node](https://github.com/Comfy-Org/workflow_templates/blob/main/site/knowledge/nodes/custom/ImageUpscaleWithModel.md) uses tiled inference to manage memory. The RTX 4060 8 GB completed the x4plus examples without CUDA OOM; peak VRAM was not separately measured.

## Local comparison

Five source images were selected across apple, banana, orange, lemon and strawberry. Each was enlarged to the same 4× pixel dimensions with (a) x2plus twice in one workflow and (b) x4plus once. A Lanczos 4× resize provided a non-model reference. All ten model outputs passed the project's file and dimension QC. Crop contact sheets in `logs/upscale_x4_benchmark/center_contact.png` and `edge_contact.png` were inspected at native pixels. The orange and banana peel structures, fruit flesh and object edges remained recognizable for both models. x2plus twice showed slightly stronger edge sharpening and bright highlights, most apparent on strawberry texture; x4plus gave a cleaner, less overprocessed appearance on this small sample. Lanczos was visibly softer and did not restore detail. The models had similar ComfyUI prompt times in the observed examples, roughly 14–16 seconds per image. This is visual judgment, not a ground-truth image-quality score.

## Production limits

The x4 output is 5016×5016 pixels for most fruit files and 6144×4096 for the whole banana. Fourfold enlargement increases pixel count 16× and can magnify invented texture in generated source images. Structural QC cannot certify realistic fruit anatomy, text/logo absence, halo-free edges or stock acceptance. Review all outputs at full size, including cutouts on dark/checkerboard backgrounds. The peeled banana and orange especially need anatomy review. The generated AI fruit set remains ineligible for contributor submission to Shutterstock; Adobe disclosure and technical/color checks remain necessary.

The final x4plus run produced 25 enlarged RGB PNGs and 25 BiRefNet transparent cutouts. All 50 jobs passed the existing structural QC; 25 transparent copies received XMP metadata with readback and pixel identity verification. Dark/checkerboard contact sheets of all 25 showed no obvious large detached background regions, but thumbnail inspection cannot clear fine edge or anatomy defects. The earlier x2plus-twice full-set output was moved to `logs/fruit_x4_x2double_archive/` as local comparison evidence, outside the final delivery folder.
