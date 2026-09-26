# Generation model refresh — 2026-09-26

## Goal and existing baseline

The current SDXL Base 1.0 route is a functional baseline, but its tested isolated objects often have gray gradient backgrounds even when prompted for pure white. The user asked to evaluate FLUX.2 [klein] and better alternatives for photostock objects. No candidate becomes the production default from a model card alone. Compare identical unbranded object briefs on the local RTX 4060 8 GB, record actual background color, shape, visible text/branding, runtime, memory and full-size visual findings. Keep benchmark images in `benchmarks/generation/`; keep `output/` empty until a real stock package passes review.

All six registries and `data/research_cache.json` were reviewed before candidate research. Official sources and licenses below were checked on 2026-09-26. The existing ComfyUI checkout is 0.37.0 at `88ab4a0`; its local code contains FLUX.2/Klein model, Qwen3 4B encoder and `EmptyFlux2LatentImage` support. This is a source compatibility check, **not** a successful run. The machine reports 8,188 MiB total GPU memory, about 6,707 MiB free with desktop apps open, 16 GB system RAM with about 4.7 GB free, and 79.5 GB free on D: before download.

## Candidate screen

| Candidate | Official license evidence | Published resource evidence | Decision for this 8 GB trial |
| --- | --- | --- | --- |
| [FLUX.2 Klein 4B distilled FP8](https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-fp8) | [Publisher Apache 2.0 license](https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-fp8/blob/main/LICENSE.md) | [ComfyUI guide](https://docs.comfy.org/tutorials/flux/flux-2-klein) reports about 8.4 GB for distilled 4B on a 5090. The official BF16 model card says about 13 GB. | **Trial candidate only** with FP8 diffusion and ComfyUI's FP4 text encoder plus low-VRAM offload. Local fit/quality unverified. |
| FLUX.2 Klein 4B Base | [Publisher Apache 2.0 model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-base-4B) | Same ComfyUI guide reports about 9.2 GB for the Base route. | Defer; heavier than distilled. |
| FLUX.2 Klein 9B | [Publisher model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-9B) lists non-commercial license | Larger model. | Excluded from commercial stock workflow. |
| [Z-Image Turbo](https://huggingface.co/Tongyi-MAI/Z-Image-Turbo) | Publisher repository lists Apache 2.0 | Publisher says full model fits in 16 GB consumer VRAM; CPU offload is documented. | Defer full weights on 8 GB. Community quantizations need separate provenance/quality checks. |
| [SANA 1.5 1.6B](https://huggingface.co/Efficient-Large-Model/SANA1.5_1.6B_1024px) | Publisher repository lists Apache 2.0 | [Official inference guide](https://github.com/NVlabs/Sana/blob/main/docs/sana.md) lists 12 GB normal, under 8 GB only with 4-bit. | Possible later quantized candidate; needs extra adapter/dependency validation. |
| [SD 3.5 Medium](https://huggingface.co/stabilityai/stable-diffusion-3.5-medium) | Stability Community License, commercial use subject to a revenue threshold | Multi-encoder route; local fit not measured. | Defer pending user/license applicability and resource benchmark. |

Published speed/VRAM figures are not results on this machine. The 4B FP8 checkpoint alone is about 4.07 GB; the complete ComfyUI trial also needs a text encoder and VAE. Even if a run fits with offloading, it may be slow or fail when desktop apps use GPU/RAM. Quality for white-background fruit/product stock must be judged from local outputs.

## Pinned FLUX.2 Klein candidate installation

Sources: [BFL FP8 publisher repository](https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-fp8/tree/5b4408e59397a4a37ccb46afe426d8ed86379441) and [Comfy-Org's Apache 2.0 ComfyUI repack](https://huggingface.co/Comfy-Org/vae-text-encorder-for-flux-klein-4b/tree/5f526678002e43af5551dadb73ce2e8c91b43afe). The exact revisions, size and SHA-256 values came from Hugging Face's file metadata; verify all downloaded bytes locally. Expected total of these three files: 8,255,049,810 bytes (7.69 GiB). They stay Git-ignored under `vendor/ComfyUI/models/`.

| Role and destination relative to `vendor/ComfyUI/models/` | Bytes | SHA-256 |
| --- | ---: | --- |
| `diffusion_models/flux-2-klein-4b-fp8.safetensors` | 4,070,624,520 | `97ed34fe0567e436200f2faee3939b88f2b5d99f8af2a4dc16532c4245c0ccb6` |
| `text_encoders/qwen_3_4b_fp4_flux2.safetensors` | 3,848,213,998 | `3eab03a77adb0ee5304a4e677d5c10ac22f9049c1d7c894adca4f8bb39206ca8` |
| `vae/flux2-vae.safetensors` | 336,211,292 | `868fe7b343cc8f3a19dbcfcafbc3d5f888802be3f89bd81b65b3621a066ce8f3` |

No custom node is required according to the local ComfyUI source inspection. Do not replace existing SDXL files. Register each installed component and its license/provenance only after hash verification. If GPU/RAM fit fails, record the failure and keep the current route. Do not update `data/research_cache.json` to select this model without a same-case local benchmark and tested production adapter.

## Comparison gate

Use the frozen cases under `benchmarks/generation/2026-09-26/cases.json`: fruit with fine anatomy, an opaque product and a thin-edged object. The two models receive the same subject description, white-background request and seed, at the same dimensions. Model-specific recommended sampler/step settings may differ and must be recorded. Run sequentially, collect timing and peak GPU use, then inspect outputs at native size. Count near-white corners only as a background diagnostic; manually inspect the entire background, subject geometry and stock defects. Review text/logos/branding explicitly. A candidate can replace SDXL only if the 8 GB run is reliable and the local quality comparison supports it; then update registry/cache, workflow/router, docs and tests together.

## Local result and selection

The four fixed 1024 × 1024 cases completed for both models on the RTX 4060 under ComfyUI `--lowvram`. The ignored local images and JSON metrics are under `benchmarks/generation/2026-09-26/output/<model-id>/`; `output/comparisons/contact_sheet.jpg` pairs each case. Board VRAM includes other desktop processes and is not a per-model allocation. The first row for each model includes loading time; subsequent rows reuse loaded weights.

| Model | Completed | Runtime per image | Peak board VRAM | Mean RGB of four corners | Full-size review of brief |
| --- | ---: | ---: | ---: | --- | --- |
| SDXL Base 1.0, 26 steps | 4/4 | 22.2–24.1 s | 7,387–7,453 MiB | 167–205 red, 125–205 green, 90–196 blue | 0/4 satisfy isolated single object on white: apple has an unwanted cutout/leaf, orange repeats across frame, mug has two handles/props, chair has gray backdrop. |
| FLUX.2 Klein 4B distilled FP8, 4 steps | 4/4 | 10.1–12.2 s | 7,470–7,604 MiB | 252–254 per channel | 4/4 meet the basic single-object/white-background brief. Fruit anatomy and edges still require stock review; orange pulp appears somewhat stylized. |

Manual inspection found no visible text, logo or branding in the eight test images. This is a small routing benchmark, not stock approval. White backgrounds in Klein images have slight off-white shading and contact shadows, so cutout requests still need the separate removal workflow and review.

**Decision:** set `flux2-klein-4b-fp8` as the provisional default for new isolated-object generation. The local router/CLI adapter was run through a frozen plan (`jobs/5c871161468942fc/plan.json`), completed as `completed_requires_review`, and its 1024 px red apple visually checked. The route snapshots and verifies all three installed component hashes before execution. SDXL remains installed as a fallback and as the explicit checkpoint for the existing SDXL creative-upscale route. There is no model download or LLM call inside the render loop. Peak board use was near the 8,188 MiB hardware limit; keep jobs sequential and expect resource pressure if other GPU apps are active. Next improvement is a broader stock review across difficult fruit/product shapes and multiple seeds before treating any output as submission-ready.
