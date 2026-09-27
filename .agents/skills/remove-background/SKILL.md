---
name: remove-background
description: Remove the background from an opaque isolated object with this project's pinned BiRefNet workflow and deterministic cutout QC. Glass and translucent subjects have no automatic route.
---

# Remove an object background

Work from the repository root. Read `docs/phase-6-results.md` for the tested path and limits. Require an explicit subject type. For opaque objects, run `.\.venv-comfyui\Scripts\python.exe scripts\remove_background.py --input <image> --subject opaque`. The script validates the registered checkpoint and license, freezes a job record, writes a transparent PNG, and reports structural QC. Do not install another model or node without the source, license, compatibility, disk and provenance checks in `AGENTS.md`.

For clear glass or sheer material, pass `--subject glass` or `--subject translucent`; this returns `unsupported_subject` without automatic output. Do not disguise those materials as opaque to force a result.

In production, use deterministic geometry, alpha, transparency, margin and file checks without agent image inspection. A `completed` result can continue to metadata and the output package. For model or system updates, inspect benchmark outputs over light, dark and checkerboard backgrounds.
