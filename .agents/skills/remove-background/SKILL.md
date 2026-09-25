---
name: remove-background
description: Remove the background from an opaque isolated object with this project's pinned BiRefNet workflow and inspect its cutout QC. Route glass and translucent subjects to manual review.
---

# Remove an object background

Work from the repository root. Read `docs/phase-6-results.md` for the tested path and limits. Require an explicit subject type. For opaque objects, run `.\.venv-comfyui\Scripts\python.exe scripts\remove_background.py --input <image> --subject opaque`. The script validates the registered checkpoint and license, freezes a job record, writes a transparent PNG, and reports structural QC. Do not install another model or node without the source, license, compatibility, disk and provenance checks in `AGENTS.md`.

For clear glass or sheer material, pass `--subject glass` or `--subject translucent`; this creates a manual-review record without automatic output. Do not disguise those materials as opaque to force a result.

Inspect the output over light, dark and checkerboard backgrounds. Confirm intact subject geometry, clean edges, removal of original floor shadow/reflection, and no text, logo, trademark, label or branding. The `manual_review_required` status is intentional. Structural QC and a clean command exit do not approve an image for photostock. Reject or regenerate suspect outputs.
