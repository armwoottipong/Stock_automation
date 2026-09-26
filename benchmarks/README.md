# Model and system experiments

`benchmarks/` holds reproducible comparisons of candidate models and checks after a new model or system update. Store input cases, candidate outputs, measurements and review contact sheets here. Registry and research-cache selections should link to a tracked result document in `docs/`; large local benchmark images stay ignored by Git.

| Area | Tracked setup and outcome | Large local files |
| --- | --- | --- |
| `background/` | Phase 5 removal manifests; result in `docs/phase-5-results.md` | `background/input/`, `background/output/` |
| `upscale_x4/2026-09-26/` | Result in `docs/x4-upscale-evaluation-2026-09-26.md` | Five-fruit comparison and x2plus-twice archive |
| `generation/2026-09-26/` | Fixed cases and candidate screen in `docs/generation-model-refresh-2026-09-26.md` | `output/` for SDXL and FLUX.2 trial results |

Keep existing Phase 5 paths because its scripts use them. New experiments get a dated directory, explicit case manifest and model/runtime record. The 2026-09-26 local comparison selected Klein provisionally for isolated-object generation; future changes require the same comparison and a tested router adapter. Keep production drafts in `staging/` and only approved submission packages in `output/`.
