"""Refresh compact model cards from the project registries and reviewed decisions."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DESTINATION = ROOT / "benchmarks" / "models"

# Editorial decisions are intentionally explicit; a new checkpoint does not inherit approval.
NOTES = {
    "flux2-klein-4b-fp8": ("Generate", "Default, provisional", "4/4 white-isolate briefs; 10.1–12.2 s; peak board VRAM 7,604 MiB.", "generation-2026-09-26.jpg", "generation-model-refresh-2026-09-26.md"),
    "sdxl-base-1.0": ("Generate / creative upscale", "Generation fallback; creative component", "0/4 isolated single-object briefs; 22.2–24.1 s. Still used by SDXL creative upscale.", "generation-2026-09-26.jpg", "generation-model-refresh-2026-09-26.md"),
    "flux2-klein-qwen3-4b-fp4": ("Klein text encoder", "Required component", "Installed and hash-verified with Klein; not a standalone image model.", "generation-2026-09-26.jpg", "generation-model-refresh-2026-09-26.md"),
    "flux2-klein-vae": ("Klein VAE", "Required component", "Installed and hash-verified with Klein; not a standalone image model.", "generation-2026-09-26.jpg", "generation-model-refresh-2026-09-26.md"),
    "birefnet-dis": ("Remove background", "Default for opaque isolates", "Cleaner opaque edges in seven-case local comparison; glass and sheer materials need manual review.", "background-2026-09-25.jpg", "phase-5-results.md"),
    "ben2-base": ("Remove background", "Compared alternative", "Seven-case comparison; less reliable than BiRefNet for opaque edges. Glass remains unresolved.", "background-2026-09-25.jpg", "phase-5-results.md"),
    "bria-rmbg-2.0": ("Remove background", "Excluded: commercial license restriction", "No local commercial benchmark or production selection.", None, "phase-5-results.md"),
    "realesrgan-x4plus": ("Pixel upscale", "Default 4×, provisional", "Five-fruit local comparison favored cleaner detail than two x2plus passes; stock review required.", "upscale-center-2026-09-26.jpg", "x4-upscale-evaluation-2026-09-26.md"),
    "realesrgan-x2plus": ("Pixel upscale", "Explicit 2× option", "Compared twice-in-series at 4×; sharper highlights than x4plus in the five-fruit sample.", "upscale-center-2026-09-26.jpg", "x4-upscale-evaluation-2026-09-26.md"),
    "xinsir-tile-sdxl-1.0": ("Creative upscale", "Registered component", "SDXL Tile ControlNet route can change subject contours; use only for reviewed creative refinement.", None, "phase-4-results.md"),
}


def main() -> None:
    records = {}
    registry_by_id = {}
    license_by_id = {
        record["resource_id"]: record
        for record in json.loads((DATA / "license_registry.json").read_text(encoding="utf-8"))["records"]
    }
    for filename in ("model_registry.json", "background_registry.json", "upscaler_registry.json", "controlnet_registry.json"):
        for record in json.loads((DATA / filename).read_text(encoding="utf-8"))["records"]:
            records[record["id"]] = record
            registry_by_id[record["id"]] = filename
    if set(records) != set(NOTES):
        raise ValueError(f"Update editorial model decisions: missing={set(records)-set(NOTES)}, obsolete={set(NOTES)-set(records)}")
    DESTINATION.mkdir(parents=True, exist_ok=True)
    rows = []
    for identifier, record in sorted(records.items()):
        role, status, result, preview, evidence = NOTES[identifier]
        license_record = license_by_id.get(identifier)
        if license_record is None or license_record["license"] != record["license"]:
            raise ValueError(f"License evidence missing or changed for {identifier}")
        lines = [
            f"# {record['name']}", "", f"- **ID:** `{identifier}`", f"- **Role:** {role}",
            f"- **Current decision:** {status}", "", result, "",
            f"- Registry: [`data/{registry_by_id[identifier]}`](../../../data/{registry_by_id[identifier]})",
            f"- License: `{record['license']}`; commercial status: `{record['commercial_use']}`; verified `{record.get('last_verified')}`.",
            f"- License evidence: [{license_record['source']}]({license_record['source']})",
            f"- Publisher/source: [{record['source']}]({record['source']})",
            f"- Installed: `{record['installed']}`; registry VRAM estimate: `{record.get('vram_gb') or 'not measured'}` GB.",
            f"- Local checkpoint: `{record.get('local_path') or 'not installed'}`",
            f"- SHA-256: `{record.get('sha256') or 'not recorded'}`",
            f"- Reviewed result: [{evidence}](../../../docs/{evidence})", "",
        ]
        if preview:
            lines += [f"![Comparison preview](../../comparisons/{preview})", "",
                      "The preview is for quick comparison; inspect native local files and the reviewed result before changing a default.", ""]
        path = DESTINATION / identifier / "README.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        rows.append(f"| [{identifier}]({identifier}/README.md) | {role} | {status} |")
    (DESTINATION / "README.md").write_text(
        "# Model inventory\n\nGenerated from the installed registries plus explicit reviewed decisions with "
        "`python scripts/build_benchmark_catalog.py`. Component cards are kept separate from standalone models.\n\n"
        "| Model | Role | Decision |\n| --- | --- | --- |\n" + "\n".join(rows) + "\n",
        encoding="utf-8",
    )
    print(f"Updated {len(records)} model cards")


if __name__ == "__main__":
    main()
