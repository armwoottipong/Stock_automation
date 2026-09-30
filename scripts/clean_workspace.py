"""Clean intermediate staging files, ComfyUI temp outputs, and stale job renders."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.audit_output import audit_set  # noqa: E402


def get_dir_size(path: Path) -> int:
    total = 0
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total


def format_bytes(bytes_val: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_val < 1024 or unit == "TB":
            return f"{bytes_val:.2f} {unit}" if unit in ["MB", "GB", "TB"] else f"{bytes_val} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} GB"


def clean_staging(root: Path, apply: bool = False) -> dict:
    staging_dir = root / "staging"
    output_dir = root / "output"
    cleaned = []
    total_bytes = 0

    if not staging_dir.exists():
        return {"category": "staging", "items": [], "reclaimed_bytes": 0}

    for set_path in sorted(staging_dir.iterdir()):
        if not set_path.is_dir():
            continue
        out_path = output_dir / set_path.name
        # Only clean if output exists and passes audit
        if out_path.is_dir() and (out_path / "set_manifest.json").exists():
            errors = audit_set(out_path)
            if not errors:
                size = get_dir_size(set_path)
                total_bytes += size
                cleaned.append({
                    "set_id": set_path.name,
                    "path": str(set_path.relative_to(root)),
                    "bytes": size,
                    "formatted": format_bytes(size),
                    "status": "audited_and_delivered",
                })
                if apply:
                    shutil.rmtree(set_path)

    return {
        "category": "staging",
        "items": cleaned,
        "count": len(cleaned),
        "reclaimed_bytes": total_bytes,
        "reclaimed_formatted": format_bytes(total_bytes),
    }


def clean_comfyui(root: Path, apply: bool = False) -> dict:
    comfy_out = root / "vendor" / "ComfyUI" / "output"
    comfy_temp = root / "vendor" / "ComfyUI" / "temp"
    total_bytes = 0
    file_count = 0

    for folder in [comfy_out, comfy_temp]:
        if not folder.exists():
            continue
        for item in folder.glob("*"):
            if item.is_file() and not item.name.startswith("."):
                size = item.stat().st_size
                total_bytes += size
                file_count += 1
                if apply:
                    try:
                        item.unlink()
                    except OSError:
                        pass

    return {
        "category": "comfyui_cache",
        "file_count": file_count,
        "reclaimed_bytes": total_bytes,
        "reclaimed_formatted": format_bytes(total_bytes),
    }


def clean_job_images(root: Path, apply: bool = False) -> dict:
    jobs_dir = root / "jobs"
    total_bytes = 0
    file_count = 0

    if not jobs_dir.exists():
        return {"category": "job_images", "file_count": 0, "reclaimed_bytes": 0}

    # Only delete rendered .png files under jobs/, preserving all JSON metadata
    for png_file in jobs_dir.rglob("*.png"):
        if png_file.is_file():
            size = png_file.stat().st_size
            total_bytes += size
            file_count += 1
            if apply:
                try:
                    png_file.unlink()
                except OSError:
                    pass

    return {
        "category": "job_images",
        "file_count": file_count,
        "reclaimed_bytes": total_bytes,
        "reclaimed_formatted": format_bytes(total_bytes),
    }


def clean_workspace(root: Path, *, staging: bool, comfyui: bool, jobs: bool, apply: bool) -> dict:
    report = {
        "mode": "apply" if apply else "dry_run",
        "results": {},
        "total_reclaimed_bytes": 0,
    }

    if staging:
        report["results"]["staging"] = clean_staging(root, apply=apply)
        report["total_reclaimed_bytes"] += report["results"]["staging"]["reclaimed_bytes"]

    if comfyui:
        report["results"]["comfyui"] = clean_comfyui(root, apply=apply)
        report["total_reclaimed_bytes"] += report["results"]["comfyui"]["reclaimed_bytes"]

    if jobs:
        report["results"]["jobs"] = clean_job_images(root, apply=apply)
        report["total_reclaimed_bytes"] += report["results"]["jobs"]["reclaimed_bytes"]

    report["total_reclaimed_formatted"] = format_bytes(report["total_reclaimed_bytes"])
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging", action="store_true", help="Clean completed staging sets that exist in output")
    parser.add_argument("--comfyui", action="store_true", help="Clean ComfyUI internal output/temp caches")
    parser.add_argument("--jobs", action="store_true", help="Prune rendered.png from jobs/ while preserving JSON metadata")
    parser.add_argument("--all", action="store_true", help="Clean all (staging, ComfyUI, job images)")
    parser.add_argument("--apply", action="store_true", help="Execute deletion (default is dry-run preview)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    args = parser.parse_args()

    do_staging = args.all or args.staging
    do_comfyui = args.all or args.comfyui
    do_jobs = args.all or args.jobs

    if not (do_staging or do_comfyui or do_jobs):
        parser.print_help()
        print("\nNote: Specify at least one target (--staging, --comfyui, --jobs, or --all). Default is dry-run.")
        return 1

    report = clean_workspace(ROOT, staging=do_staging, comfyui=do_comfyui, jobs=do_jobs, apply=args.apply)

    if args.json:
        print(json.dumps(report, indent=2))
        return 0

    mode_str = "APPLIED CLEANUP" if args.apply else "DRY-RUN PREVIEW (pass --apply to execute)"
    print(f"\n=======================================================")
    print(f"  WORKSPACE CLEANUP REPORT [{mode_str}]")
    print(f"=======================================================\n")

    if "staging" in report["results"]:
        stg = report["results"]["staging"]
        print(f"Staging Sets Cleaned: {stg['count']} sets ({stg['reclaimed_formatted']})")
        for item in stg["items"]:
            print(f"  - {item['set_id']}: {item['formatted']}")

    if "comfyui" in report["results"]:
        comfy = report["results"]["comfyui"]
        print(f"\nComfyUI Output Cache: {comfy['file_count']} files ({comfy['reclaimed_formatted']})")

    if "jobs" in report["results"]:
        jb = report["results"]["jobs"]
        print(f"\nJob Rendered Images: {jb['file_count']} images ({jb['reclaimed_formatted']})")

    print(f"\n-------------------------------------------------------")
    print(f"Total Disk Space Reclaimed: {report['total_reclaimed_formatted']}")
    print(f"-------------------------------------------------------\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
