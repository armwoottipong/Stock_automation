# Phase 5 background model comparison plan — 2026-09-25

**Status:** approved, downloaded, SHA-256 verified and benchmarked. See [Phase 5 results](phase-5-results.md) for the subject-scoped decision and limitations.

## Hardware and execution

- Target: Windows 11, RTX 4060 with 8,188 MiB VRAM, Python 3.12 and CUDA PyTorch in `.venv-comfyui`.
- Drive D has about 92.1 GB free before this phase. Reserve at least 10 GB for weights, package caches, inputs and outputs.
- Run candidates one at a time in a Python process, with ComfyUI idle or stopped. This avoids adding an unverified custom node and leaves the existing render loop unchanged. A future Phase 6 adapter can call the pinned Python inference code.
- Measure peak allocated and reserved CUDA memory, wall time, failure/OOM, image dimensions, alpha range and geometry on this machine. Published model size does **not** establish 8 GB inference fit.

## Shortlist and license gate

| Candidate | Official weights and integrity | License evidence | Expected integration |
| --- | --- | --- | --- |
| BiRefNet standard DIS | [Publisher checkpoint](https://huggingface.co/ZhengPeng7/BiRefNet/blob/6a62b7dcfa18a3829087877fb16c8006831e4220/model.safetensors), 444,473,596 bytes, SHA-256 `9ab37426bf4de0567af6b5d21b16151357149139362e6e8992021b8ce356a154` | [Publisher model card](https://huggingface.co/ZhengPeng7/BiRefNet) and [MIT source license](https://github.com/ZhengPeng7/BiRefNet/blob/main/LICENSE), checked 2026-09-25 | Publisher Python/Transformers inference at 1024 px; pin and inspect remote code before enabling it |
| BEN2 **Base** | [Publisher checkpoint](https://huggingface.co/PramaLLC/BEN2/blob/19d0d22912541ae3178d10682640616c7287957b/model.safetensors), about 381 MB, SHA-256 `ea8b7907176a09667c86343dc7d00de6a6d871076cb90bb5f753618fd6fb3ebb` | [Publisher model card](https://huggingface.co/PramaLLC/BEN2) identifies Base as open source; [MIT source license](https://github.com/PramaLLC/BEN2/blob/main/LICENSE), checked 2026-09-25 | Publisher `BEN_Base` Python inference, batch size 1; no commercial refiner or service |

Both are **license-eligible candidates**, not production defaults. Their dependency code and exact checkout revisions must be reviewed and recorded before installation. BiRefNet's documented Hugging Face loader uses `trust_remote_code=True`; use only a pinned, inspected revision. BEN2's full enhanced/commercial model is separate from Base and is out of scope.

The [BRIA RMBG-2.0 publisher card](https://huggingface.co/briaai/RMBG-2.0) says its self-hosted weights are noncommercial without a separate agreement, so it is excluded. [InSPyReNet/transparent-background](https://github.com/plemeri/transparent-background) remains an optional third candidate if the first two fail; its checkpoint provenance and redistribution terms need further verification before download.

## Proposed download after approval

1. Download only the two pinned `model.safetensors` files above to a Git-ignored local model cache. Verify the published SHA-256 before use. Approximate combined weight size is 826 MB; package/cache overhead is additional.
2. Install only dependencies required by the inspected pinned inference code. Record package versions, source revisions, exact paths and hashes in the relevant registries. Avoid pickle checkpoints and automatic unpinned downloads.
3. Keep background inference separate from the live ComfyUI process for the benchmark. Verify CUDA execution and actual peak VRAM on the RTX 4060.

## Small benchmark and decision rule

Use the frozen Isolate generation plan as the primary small benchmark: fur object, opaque product, glass, translucent craft object, furniture, thin structures, and complex shadow/reflection. Record requested and measured background color and input provenance; use the same images, resolution and preprocessing for both candidates. Generated gray studio backgrounds are acceptable for this Isolate comparison but cannot prove performance on literal white inputs. Retain the earlier mixed-scene set as a secondary robustness check.

For each output, record runtime, peak VRAM, errors, alpha validity, edge halo, retained fine structures, unwanted background, shape changes, transparency handling and shadow/reflection removal. Review masks over light, dark and checkerboard backgrounds. A clean cutout means original floor reflection and shadow are removed unless a job explicitly asks to keep them.

Choose a default only if a candidate fits 8 GB, passes license/provenance checks and the small benchmark, and meets the geometry and clean-cutout requirements. Record a subject-specific fallback where one model is clearly better. Otherwise leave the default unset and document the failure. Phase 6 implements matte refinement and QC after this selection.
