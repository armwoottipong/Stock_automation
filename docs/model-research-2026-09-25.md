# Phase 3 checkpoint research — 2026-09-25

Target: Windows, RTX 4060 8 GB, local ComfyUI 0.37.0, SDXL generation, commercial images.

| Candidate | Evidence | Commercial status for this project | 8 GB status | Decision |
| --- | --- | --- | --- | --- |
| [SDXL Base 1.0](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0) | [Official model card and weights](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/tree/462165984030d82259a11f4367a4eed129e94a7b), [CreativeML Open RAIL++-M license](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/462165984030d82259a11f4367a4eed129e94a7b/LICENSE.md) | Allowed for ordinary commercial images, subject to the license's use restrictions. The license does not claim rights in generated output. | One 1024 px, 26-step `--lowvram` run passed; about 7.1 GB GPU memory observed. | **Phase 3 default for functional validation.** Official provenance and a full license are available. |
| [RealVisXL V5.0](https://huggingface.co/SG161222/RealVisXL_V5.0) | Creator's model card labels OpenRAIL++ and describes photorealism. The creator's [Civitai model metadata](https://civitai.com/api/v1/models/139562) lists commercial image use but `allowNoCredit: false`. | Restricted pending a clear attribution policy for this project's intended outputs. | Not measured. fp16 checkpoint is 6.94 GB. | Candidate for later photoreal quality comparison; do not auto-enable for commercial jobs. |
| [RealVisXL V4.0](https://huggingface.co/SG161222/RealVisXL_V4.0) | Creator model card labels OpenRAIL++; checkpoint is 6.94 GB. Same Civitai model-level permissions appear to apply. | Restricted pending attribution clarification. | Not measured. | Fallback comparison candidate only. |

The SDXL Base checkpoint is a functional baseline, not a claim that it produces the best photorealistic images. RealVisXL could outperform it for that purpose, but quality must be judged using a small local benchmark after its use terms are resolved. SDXL Base is installed locally and passed one low-VRAM smoke run. Do not infer all-job VRAM fit from a single result.

The selected SDXL file is `sd_xl_base_1.0.safetensors` at repository revision `462165984030d82259a11f4367a4eed129e94a7b`. The [official file page](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/462165984030d82259a11f4367a4eed129e94a7b/sd_xl_base_1.0.safetensors) lists size 6.94 GB and SHA-256 `31e35c80fc4829d14f90153f4c74cd59c90b779f6afe05a74cd6120b893f7e5b`.
