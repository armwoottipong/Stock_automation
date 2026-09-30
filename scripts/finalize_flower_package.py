"""Finalize packaging for the 200 flower set and run audit."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "staging" / "flowers_200_2026-09-29"
PACKAGES_DIR = STAGING / "packages"
ADOBE_PKG = PACKAGES_DIR / "adobe_stock"
WHITE_PKG = PACKAGES_DIR / "white_png_companion"
RAW_DIR = STAGING / "raw_1024"


def finalize():
    # 1. Ensure csv is in adobe_stock package
    csv_src = STAGING / "adobe_stock.csv"
    csv_dst = ADOBE_PKG / "adobe_stock.csv"
    shutil.copy2(csv_src, csv_dst)

    # 2. Build submission_manifest.json for adobe_stock
    adobe_pngs = sorted([p.name for p in ADOBE_PKG.glob("*.png")])
    if len(adobe_pngs) != 200:
        raise ValueError(f"Expected 200 pngs in adobe_stock, got {len(adobe_pngs)}")

    adobe_manifest = {
        "platform": "adobe_stock",
        "source_type": "generative_ai",
        "adobe_ai_disclosure_required": True,
        "checks": {
            "metadata": True,
            "technical": True,
            "rights": True,
        },
        "image_count": len(adobe_pngs),
        "assets": [*adobe_pngs, "adobe_stock.csv"],
        "source_set": "flowers_200_2026-09-29",
        "submission_note": "Technically prepared transparent-PNG assets for Adobe Stock. Select Created using generative AI tools in the Adobe Contributor Portal.",
    }
    (ADOBE_PKG / "submission_manifest.json").write_text(
        json.dumps(adobe_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("Created adobe_stock submission_manifest.json")

    # 3. Create white_png_companion package
    WHITE_PKG.mkdir(parents=True, exist_ok=True)
    raw_pngs = sorted(list(RAW_DIR.glob("*.png")))
    if len(raw_pngs) != 200:
        raise ValueError(f"Expected 200 raw pngs, got {len(raw_pngs)}")

    white_assets = []
    for p in raw_pngs:
        target = WHITE_PKG / p.name
        if not target.exists():
            shutil.copy2(p, target)
        white_assets.append(p.name)

    white_manifest = {
        "platform": "local_delivery",
        "package_purpose": "white_png_companion",
        "source_type": "generative_ai",
        "checks": {
            "metadata": True,
            "technical": True,
            "rights": True,
        },
        "image_count": len(white_assets),
        "source_set": "flowers_200_2026-09-29",
        "assets": white_assets,
        "submission_note": "Solid-white PNG companions; not Adobe Stock transparent-PNG submission assets.",
    }
    (WHITE_PKG / "submission_manifest.json").write_text(
        json.dumps(white_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("Created white_png_companion package and submission_manifest.json")

    # 4. Package set
    cmd_package = [
        sys.executable,
        str(ROOT / "scripts" / "package_stock_set.py"),
        "--set-id",
        "flowers_200_2026-09-29",
        "--packages",
        str(ADOBE_PKG),
        str(WHITE_PKG),
    ]
    print("Running package_stock_set.py ...", flush=True)
    res_pkg = subprocess.run(cmd_package, cwd=ROOT, capture_output=True, text=True)
    if res_pkg.returncode != 0:
        print("Packaging stderr:", res_pkg.stderr)
        raise RuntimeError("Failed to package stock set")
    print(res_pkg.stdout.strip())

    # 5. Audit output
    cmd_audit = [sys.executable, str(ROOT / "scripts" / "audit_output.py")]
    res_audit = subprocess.run(cmd_audit, cwd=ROOT, capture_output=True, text=True)
    if res_audit.returncode != 0:
        print("Audit stderr:", res_audit.stderr)
        raise RuntimeError("Audit failed")
    print(res_audit.stdout.strip())
    print("Final packaging and audit completed successfully!")


if __name__ == "__main__":
    finalize()
