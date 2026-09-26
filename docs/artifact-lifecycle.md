# Artifact lifecycle

## Directories

| Location | Purpose |
| --- | --- |
| `jobs/` | Frozen plans, execution checkpoints, raw controller results and per-job QC. |
| `logs/` | Runtime logs and temporary diagnostics. |
| `staging/` | Generated or processed image sets, metadata drafts and packages awaiting human and technical stock review. |
| `benchmarks/` | Model comparisons and system-update experiments: test inputs, outputs, measurements and contact sheets. |
| `output/` | Only reviewed packages ready to submit to a named platform. |

New model installations still require official source, license, compatibility, space and provenance checks before any benchmark. Record the installed candidate and SHA-256 in the registry. After comparing it with the current model on representative inputs, write a result document under `docs/` and update the research cache only when the evidence supports selection. Put large local comparison files under `benchmarks/`, not `output/`.

## Moving a draft to final output

1. Review every selected image at full size for subject geometry, artifacts, cutout edges, shadow/reflection, visible text, logos, trademarks, branding and overly similar variants. Record the human decision.
2. Confirm commercial rights, technical format, size and sRGB, and platform-appropriate title/keywords and metadata import. Check the current platform submission rules. For Adobe AI assets, record that the Contributor Portal AI disclosure is required; do not route contributor AI assets to Shutterstock.
3. Create a package directory under `output/` with the exact deliverables and `submission_manifest.json`. Its status must be `ready_to_submit`; `checks.visual_review`, `checks.metadata`, `checks.technical` and `checks.rights` must all be `true`. Include every package file in `assets` using relative paths.
4. Run `python scripts/audit_output.py`. A passing audit checks the package record and file inventory; it does not replace manual review or approval by the stock platform.

The 2026-09-26 fruit set remains under `staging/` because its full-size visual review, sRGB/format checks and submission curation are outstanding. `output/` currently has no approved package.
