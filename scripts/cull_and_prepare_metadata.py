"""Cull raw generated images and pre-generate stock metadata using Gemini API."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_image_automation.gemini_service import (
    dual_inspect_candidate,
    generate_stock_metadata,
)


def run_cull_and_prepare_metadata(
    staging_dir: Path,
    raw_subfolder: str = "raw_1024",
    manifest_path: Path | None = None,
    model_metadata: str = "gemini-3.1-flash-lite",
    model_qc_primary: str = "gemini-3.1-flash-lite",
    model_qc_secondary: str = "gemini-3.5-flash-lite",
    pause_seconds: float = 3.0,
) -> dict:
    staging_dir = Path(staging_dir).resolve()
    raw_dir = staging_dir / raw_subfolder
    rejected_dir = staging_dir / "rejected_raw"

    if not raw_dir.is_dir():
        raise FileNotFoundError(f"Raw image directory not found: {raw_dir}")

    rejected_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load item descriptions from manifest if available
    descriptions: dict[str, str] = {}
    m_path = manifest_path or (staging_dir / "items_manifest.json")
    if m_path.exists():
        try:
            m_data = json.loads(m_path.read_text(encoding="utf-8"))
            for rec in m_data.get("records", []):
                item_id = rec.get("id") or Path(rec.get("raw_image", "")).stem
                desc = rec.get("description") or rec.get("prompt", "")
                if item_id and desc:
                    descriptions[item_id] = desc
        except Exception as exc:
            print(f"Warning: could not parse items manifest ({exc}). Falling back to filenames.")

    raw_images = sorted(list(raw_dir.glob("*.png")) + list(raw_dir.glob("*.jpg")) + list(raw_dir.glob("*.jpeg")))
    total_images = len(raw_images)
    print(f"\n=======================================================", flush=True)
    print(f"Gemini Pre-Metadata & Culling Gate: {staging_dir.name}", flush=True)
    print(f"Total raw candidates found: {total_images}", flush=True)
    print(f"=======================================================\n", flush=True)

    # 2. Pre-generate Metadata & store in draft_metadata.json
    draft_meta_file = staging_dir / "draft_metadata.json"
    draft_metadata: dict[str, dict] = {}
    if draft_meta_file.exists():
        try:
            draft_metadata = json.loads(draft_meta_file.read_text(encoding="utf-8"))
        except Exception:
            draft_metadata = {}

    print("--- STEP 1: Pre-generating Stock Metadata (Gemini API) ---", flush=True)
    for idx, img_path in enumerate(raw_images, start=1):
        stem = img_path.stem
        if stem in draft_metadata:
            continue

        desc = descriptions.get(stem, stem.replace("_", " "))
        print(f"[{idx}/{total_images}] Generating metadata for '{stem}'...", flush=True)
        try:
            meta = generate_stock_metadata(
                description=desc,
                model=model_metadata,
                image_path=img_path,
            )
            draft_metadata[stem] = {
                "id": stem,
                "description": desc,
                "title": meta["title"],
                "category": meta.get("category", 3),
                "keywords": meta["keywords"],
                "generated_at": time.time(),
            }
            # Save checkpoint
            draft_meta_file.write_text(json.dumps(draft_metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            print(f"  Error generating metadata for {stem}: {exc}", flush=True)

        time.sleep(pause_seconds)

    print(f"Step 1 completed. Saved {len(draft_metadata)} draft metadata records.\n", flush=True)

    # 3. Vision Culling Gate with Gemini 3.1 & 3.5 Flash Lite
    culling_report_file = staging_dir / "culling_report.json"
    culling_report: dict[str, dict] = {}
    if culling_report_file.exists():
        try:
            culling_report = json.loads(culling_report_file.read_text(encoding="utf-8"))
        except Exception:
            culling_report = {}

    print("--- STEP 2: Dual-Vision QC Inspection (Gemini 3.1 & 3.5 Flash Lite) ---", flush=True)
    passed_items: list[str] = []
    rejected_items: list[str] = []

    for idx, img_path in enumerate(raw_images, start=1):
        stem = img_path.stem
        if stem in culling_report:
            item_res = culling_report[stem]
        else:
            desc = descriptions.get(stem, stem.replace("_", " "))
            print(f"[{idx}/{total_images}] Inspecting '{stem}' with dual models...", flush=True)
            try:
                eval_res = dual_inspect_candidate(
                    image_path=img_path,
                    description=desc,
                    model_primary=model_qc_primary,
                    model_secondary=model_qc_secondary,
                )
                item_res = {
                    "id": stem,
                    "filename": img_path.name,
                    "pass": eval_res["pass"],
                    "primary": eval_res["primary_model"],
                    "secondary": eval_res["secondary_model"],
                    "defects": eval_res.get("defects_detected", []),
                    "reasons": eval_res.get("rejection_reasons", []),
                    "evaluated_at": time.time(),
                }
                culling_report[stem] = item_res
                culling_report_file.write_text(json.dumps(culling_report, indent=2, ensure_ascii=False), encoding="utf-8")
            except Exception as exc:
                print(f"  Error during inspection of {stem}: {exc}", flush=True)
                item_res = {"id": stem, "pass": False, "reasons": [str(exc)]}

            time.sleep(pause_seconds)

        if item_res.get("pass", False):
            passed_items.append(stem)
            print(f"  -> [PASS] '{stem}' passed Adobe Stock inspection.")
        else:
            rejected_items.append(stem)
            reasons_str = "; ".join(item_res.get("reasons", ["Failed QC"]))
            print(f"  -> [REJECT] '{stem}' rejected: {reasons_str}")
            # Move rejected raw file out of raw_1024 to rejected_raw/
            target_reject = rejected_dir / img_path.name
            if img_path.exists() and not target_reject.exists():
                shutil.move(img_path, target_reject)

    summary = {
        "staging_dir": str(staging_dir),
        "total_evaluated": total_images,
        "passed_count": len(passed_items),
        "rejected_count": len(rejected_items),
        "passed_items": passed_items,
        "rejected_items": rejected_items,
    }
    (staging_dir / "culling_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("\n=======================================================", flush=True)
    print(f"Culling Complete: {len(passed_items)} Passed, {len(rejected_items)} Rejected", flush=True)
    print(f"Only passed candidates remain in {raw_dir} for 4K upscale/cutout.", flush=True)
    print("=======================================================\n", flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description="Pre-generate metadata and cull raw stock candidates using Gemini API")
    parser.add_argument("--staging-dir", type=Path, required=True, help="Path to staging/<SET_ID> folder")
    parser.add_argument("--raw-subfolder", default="raw_1024", help="Subfolder containing raw images")
    parser.add_argument("--manifest", type=Path, default=None, help="Path to items manifest JSON with prompts")
    parser.add_argument("--model-meta", default="gemini-3.1-flash-lite", help="Gemini model for metadata")
    parser.add_argument("--model-qc1", default="gemini-3.1-flash-lite", help="Primary Gemini model for QC")
    parser.add_argument("--model-qc2", default="gemini-3.5-flash-lite", help="Secondary Gemini model for QC")
    parser.add_argument("--pause", type=float, default=3.0, help="Delay between API calls in seconds (for RPM limits)")
    args = parser.parse_args()

    run_cull_and_prepare_metadata(
        staging_dir=args.staging_dir,
        raw_subfolder=args.raw_subfolder,
        manifest_path=args.manifest,
        model_metadata=args.model_meta,
        model_qc_primary=args.model_qc1,
        model_qc_secondary=args.model_qc2,
        pause_seconds=args.pause,
    )


if __name__ == "__main__":
    main()
