# Phase 5 background model comparison — 2026-09-25

## Decision

The target workflow is **unbranded object imagery on a white or simple solid studio background** for photostock. The seven locally generated Isolate cases are the primary benchmark. BiRefNet standard DIS is the **provisional model choice for opaque isolated objects**, including fur, a mug, furniture, a bicycle and a bottle with floor reflection. BEN2 Base remains an installed, evaluated alternative. Neither model is approved for automatic glass or sheer fabric cutouts. Phase 6 must implement matte refinement, source-color decontamination and review routing before those subjects can be delivered.

This is a Phase 5 model choice, not a production background-removal workflow. The required output policy is a clean cutout that removes the source shadow and floor reflection while preserving subject geometry. Text, logos, trademarks, labels and other branding must also be absent from stock deliverables. Prompt exclusions lower their incidence but do not certify an image; a human must inspect every final image for these defects.

## Provenance and hardware

The [installation plan](phase-5-install-plan.md) records publisher sources, official MIT license evidence, pinned revisions and SHA-256 values. The user approved both downloads. The local hashes matched.

| Model | Checkpoint bytes | Verified SHA-256 | Peak PyTorch allocated / reserved |
| --- | ---: | --- | ---: |
| BiRefNet standard DIS | 444,473,596 | `9ab37426bf4de0567af6b5d21b16151357149139362e6e8992021b8ce356a154` | 1.584 / 2.967 GiB |
| BEN2 Base | 380,577,976 | `ea8b7907176a09667c86343dc7d00de6a6d871076cb90bb5f753618fd6fb3ebb` | 2.340 / 3.143 GiB |

Test host: Windows 11, NVIDIA RTX 4060 8,188 MiB, CUDA PyTorch 2.14.0+cu130, torchvision 0.29.0+cu130, timm 1.0.30 and opencv-python-headless 4.12.0.88. The last two packages were added to the existing ComfyUI venv. An initial timm 1.0.23 install failed a legacy import, so it was upgraded. Transformers 5.17 could not load the publisher's older BiRefNet class; the benchmark instead imports pinned local publisher source and reads the verified safetensors directly. It does not fetch code or weights during inference. Peak VRAM is process-local PyTorch memory; driver and other processes are excluded. Both seven-image runs finished without OOM.

## Primary benchmark: isolated objects

[Frozen generation settings](../benchmarks/background/isolated_generation.json) request seven 1024 × 1024 unbranded objects on pure white backgrounds, with negative prompts for text, logos, trademarks and watermarks. [Case metadata](../benchmarks/background/isolated_cases.json) identifies each file and records the actual top-left corner color. Inputs and outputs are ignored by Git. The same input files were given to both models. Masks, cutouts and per-case JSON are under `benchmarks/background/output/isolated/<model-id>/`; checkerboard sheets are under `benchmarks/background/output/comparisons/isolated/`.

**Generation limitation:** SDXL produced smooth gray studio gradients despite every prompt requesting pure white. The corner mean RGB values span roughly 82–167 rather than near 255; all seven `near_white_corner` checks are false. These images represent simple Isolate scenes, but they do **not** validate performance on literal white backgrounds. The generation workflow needs a white-background acceptance check and regeneration or correction path before it can supply stock-ready inputs. Corner sampling is only a fixture diagnostic, not proof that a whole background is white.

Median inference time after the first warmup image was **0.256 s** for BiRefNet and **0.347 s** for BEN2 Base. Both preserved the source 1024 × 1024 dimensions and exact RGB pixels, changing alpha only. This preserves the original subject colors but means transparent glass and fabric can retain gray source-background color. The models therefore need color decontamination for those materials.

| Case | Visual review on checkerboard |
| --- | --- |
| Fluffy teddy bear | BiRefNet retains a crisp fur outline; BEN2 has more hazy, partly transparent edge pixels. |
| Opaque ceramic mug | Both retain the body and handle; BiRefNet gives a cleaner opaque edge. |
| Clear drinking glass | BiRefNet introduces some interior transparency; BEN2 is largely gray/opaque. Neither yields a reliably clean transparent object. |
| Sheer organza ribbon | BEN2 gives much more partial transparency; BiRefNet tends to make the fabric opaque. Neither has validated color or opacity for a final cutout. |
| Wooden chair | Both keep legs and open spaces; BiRefNet has the cleaner edge. |
| Bicycle with spokes | Both retain major frame geometry; BiRefNet leaves less ghost opacity in gaps. |
| Perfume bottle and floor reflection | Both keep the bottle and remove the original floor reflection/shadow; BiRefNet's bottom edge is slightly tighter. |

To repeat the local run with the generated inputs:

```powershell
python scripts\generate_isolated_fixtures.py
.\.venv-comfyui\Scripts\python.exe scripts\benchmark_background.py --manifest isolated_cases.json --model birefnet-dis
.\.venv-comfyui\Scripts\python.exe scripts\benchmark_background.py --manifest isolated_cases.json --model ben2-base
.\.venv-comfyui\Scripts\python.exe scripts\review_background_benchmark.py --manifest isolated_cases.json
```

The prior [mixed-scene manifest](../benchmarks/background/cases.json) is a secondary robustness check: five Wikimedia Commons images plus one local perfume fixture, seven categories and six unique images. BiRefNet's post-warmup median there was 0.279 s versus BEN2's 0.385 s. Both failed to make the scene glass and curtain reliably transparent. Mixed scenes are less representative of the product's intended input.

## Limits and next phase

There are no hand-labeled reference mattes, and only one image per Isolate category. Visual findings are narrow and do not establish photostock acceptance. No image has been automatically cleared of text or branding: that needs explicit final review. Phase 6 should implement the opaque BiRefNet path, deterministic alpha/edge and geometry checks, shadow/reflection removal checks, white/solid-background input checks, and manual review for transparent subjects and stock-content defects. Create a reusable `remove-background` skill only after the workflow passes those gates.
