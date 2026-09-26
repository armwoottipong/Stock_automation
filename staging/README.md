# Work awaiting stock review

Use `staging/` for generated images, upscale/cutout results, metadata drafts and ZIP packages before final approval. A structurally valid cutout or embedded XMP is not sufficient for `output/`.

The 2026-09-26 fruit set is in `fruit_isolates_2026-09-26/`; its historical and 4× review ZIPs are in `packages/`. These AI-generated files require full-size content and edge review, rights confirmation, Adobe format/color checks, similarity curation and the Adobe Contributor Portal AI disclosure. They are not eligible for Shutterstock contributor submission under current policy.

Move only approved submission packages to `output/` and provide a `submission_manifest.json` that passes `python scripts/audit_output.py`.
