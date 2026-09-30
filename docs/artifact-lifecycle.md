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
2. Prepare package directories under `staging/<set>/packages/`:
   - An audited platform package (e.g., `adobe_stock/` containing strictly 100% transparent PNG images — zero JSON or CSV files).
   - A companion JPEG package (e.g., `white_jpeg_companion/` containing strictly 100% white-background JPEGs with embedded XMP — zero JSON or CSV files).
   - A dedicated metadata package (`metadata/` containing `adobe_stock.csv`, `catalog.json`, `contact_sheet_4k.jpg`, and all package manifests `<package>_manifest.json`, with `package_purpose: "metadata_companion"`).
   - This ensures image folders contain exclusively image deliverables, making drag-and-drop batch upload directly to contributor portals seamless and error-free.
3. Package manifests are stored in the sibling `metadata/` package (e.g. `adobe_stock_manifest.json`, `white_jpeg_companion_manifest.json`) or directly inside the package if standalone. Run `python scripts/package_stock_set.py --set-id <set-id> --packages <package-dir> [<companion-dir>]` to produce exactly one `output/<set-id>/` folder. The command verifies each package, checks copied-file hashes, writes `set_manifest.json` listing internal packages, and refuses to overwrite an existing set. Run `python scripts/audit_output.py` before delivery. Audit checks safe paths, structure and deterministic declarations, not visual quality or stock platform acceptance.
4. After delivery, intermediate staging files (`staging/<set>/raw_1024`, `upscaled_4k`, `cutout_4k`, `packages`) are automatically cleaned via `run_4k_stock_pipeline.py` or `python scripts/clean_workspace.py --staging --apply`. The delivered package in `output/` is self-contained with its images, contact sheet, and metadata.
5. The user may inspect deliverables and cull images with bad geometry, artifacts, cutout edges, shadows/reflections, visible text/logos/branding, similarity or metadata mismatches. Rework only if requested.

## Long-term workspace hygiene

To prevent junk files and disk bloat in the long run:
- **Staging Cleanup**: Intermediate generation, upscale, and cutout images are purged after successful delivery.
- **ComfyUI Cache**: Temporary node output files in `vendor/ComfyUI/output` and `vendor/ComfyUI/temp` are pruned periodically.
- **Job Images**: Completed job `.png` renders in `jobs/` can be pruned while preserving all JSON metadata for deterministic reproducibility.
- **Command**: Run `python scripts/clean_workspace.py --all --apply` (or with `--dry-run` to preview).

