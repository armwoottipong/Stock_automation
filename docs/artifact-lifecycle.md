# Artifact lifecycle

## Directories

| Location | Purpose |
| --- | --- |
| `jobs/` | Frozen plans, execution checkpoints, raw controller results and per-job QC. |
| `logs/` | Runtime logs and temporary diagnostics. |
| `staging/` | Generated or processed image sets, technical preparation, metadata, previews and contact sheets. |
| `benchmarks/` | Model comparisons and system-update experiments: test inputs, outputs, measurements and contact sheets. |
| `output/` | One audited folder per requested set; platform assets and local companion assets are grouped inside that folder. No ZIP delivery. |

New model installations still require official source, license, compatibility, space and provenance checks before any benchmark. Record the installed candidate and SHA-256 in the registry. After comparing it with the current model on representative inputs, write a result document under `docs/` and update the research cache only when the evidence supports selection. Put large local comparison files under `benchmarks/`, not `output/`.

## Moving a prepared set to output

1. Run deterministic QC and confirm commercial rights, technical format, size, sRGB, and platform-appropriate metadata. Check current platform rules. For Adobe AI assets, record that the Contributor Portal AI disclosure is required; do not route contributor AI assets to Shutterstock.
2. Prepare a contact sheet and package directories under `staging/<set>/packages/`. Copy every structurally valid exact upload file plus platform CSV into the appropriate package. The agent does not inspect images during production, and there is no user approval pause.
3. Add `submission_manifest.json` to each internal package without image-review status or visual-review fields, with truthful metadata, technical and rights checks. List every package file in `assets`. Run `python scripts/package_stock_set.py --set-id <set-id> --packages <package-dir> [<companion-dir>]` to produce exactly one `output/<set-id>/` folder. The command verifies each package, checks copied-file hashes, writes `set_manifest.json` listing internal packages, and refuses to overwrite an existing set. Run `python scripts/audit_output.py` before delivery. Audit checks safe paths, structure and deterministic declarations, not visual quality or stock platform acceptance.
4. After delivery, the user may remove images with bad geometry, artifacts, cutout edges, shadows/reflections, visible text/logos/branding, similarity or metadata mismatches. Rework only if requested.

If a request also needs white-background PNGs, place them in a labeled `local_delivery` subdirectory inside the same set folder, with `package_purpose: white_png_companion`. Keep its manifest separate from the Adobe assets. Adobe Stock's PNG route requires transparency, so do not present solid-white PNGs as Adobe PNG submission assets. Multiple formats from the same request must not create multiple directories at the top level of `output/`.

The 2026-09-26 fruit set is delivered in `output/fruit_isolates_2026-09-26_new/`. The 2026-09-27 apple request is delivered in `output/apple_white_cutout_2026-09-27_001/`, containing both transparent and white PNG packages. Their contact sheets and preparation evidence remain under their respective staging identities.
