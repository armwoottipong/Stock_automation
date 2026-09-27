# Artifact lifecycle

## Directories

| Location | Purpose |
| --- | --- |
| `jobs/` | Frozen plans, execution checkpoints, raw controller results and per-job QC. |
| `logs/` | Runtime logs and temporary diagnostics. |
| `staging/` | Generated or processed image sets, technical preparation, metadata, previews and contact sheets. |
| `benchmarks/` | Model comparisons and system-update experiments: test inputs, outputs, measurements and contact sheets. |
| `output/` | Audited platform packages and explicitly labeled local companion packages with deterministic checks and no image-review gate. |

New model installations still require official source, license, compatibility, space and provenance checks before any benchmark. Record the installed candidate and SHA-256 in the registry. After comparing it with the current model on representative inputs, write a result document under `docs/` and update the research cache only when the evidence supports selection. Put large local comparison files under `benchmarks/`, not `output/`.

## Moving a prepared set to output

1. Run deterministic QC and confirm commercial rights, technical format, size, sRGB, and platform-appropriate metadata. Check current platform rules. For Adobe AI assets, record that the Contributor Portal AI disclosure is required; do not route contributor AI assets to Shutterstock.
2. Prepare a contact sheet in staging and copy every structurally valid exact upload file plus platform CSV into a new `output/<platform-set>/` package. The agent does not inspect images during production, and there is no user approval pause.
3. Add `submission_manifest.json` without image-review status or visual-review fields, with truthful metadata, technical and rights checks. List every package file in `assets`. Run `python scripts/audit_output.py` before delivery. Audit checks structure and deterministic declarations, not visual quality or stock platform acceptance.
4. After delivery, the user may remove images with bad geometry, artifacts, cutout edges, shadows/reflections, visible text/logos/branding, similarity or metadata mismatches. Rework only if requested.

If a request also needs white-background PNGs, place them in a separate `local_delivery` package with `package_purpose: white_png_companion`. Adobe Stock's PNG route requires transparency, so do not present solid-white PNGs as Adobe PNG submission assets.

The new 2026-09-26 fruit set is delivered in `output/adobe_fruit_isolates_2026-09-26_new/` as a technically prepared package. Its contact sheet and preparation evidence remain in `staging/fruit_isolates_new_2026-09-26/`.
