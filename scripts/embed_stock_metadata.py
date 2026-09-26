"""Write title and keywords into XMP of review copies, preserving source files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_image_automation.stock_metadata import MetadataError, load_catalog, validate_catalog  # noqa: E402


def pixel_digest(path: Path) -> str:
    with Image.open(path) as image:
        return hashlib.sha256(image.mode.encode() + str(image.size).encode() + image.tobytes()).hexdigest()


def embed(catalog_path: Path, assets: Path, output: Path, platform: str) -> dict:
    catalog = load_catalog(catalog_path)
    validate_catalog(catalog, platform, assets)
    executable = shutil.which("exiftool")
    if executable is None:
        raise MetadataError("ExifTool is required to embed XMP")
    if assets.resolve() == output.resolve():
        raise MetadataError("Output must differ from source asset directory")
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    env["LANG"] = "C"
    results = []
    for item in catalog["records"]:
        source = assets / item["filename"]
        target = output / item["filename"]
        before = pixel_digest(source)
        shutil.copy2(source, target)
        command = [
            executable, "-overwrite_original", "-q", "-q", "-sep", "|",
            f"-XMP-dc:Title={item['title']}",
            f"-XMP-dc:Description={item['title']}",
            f"-XMP-dc:Subject={'|'.join(item['keywords'])}",
            str(target),
        ]
        subprocess.run(command, check=True, capture_output=True, text=True, env=env)
        if pixel_digest(target) != before:
            target.unlink(missing_ok=True)
            raise MetadataError(f"Image pixels changed: {item['filename']}")
        results.append({"filename": item["filename"], "pixel_sha256": before})
    readback = subprocess.run(
        [executable, "-j", "-XMP-dc:Title", "-XMP-dc:Description", "-XMP-dc:Subject", *[str(output / item["filename"]) for item in catalog["records"]]],
        check=True, capture_output=True, text=True, env=env,
    )
    extracted = {Path(row["SourceFile"]).name: row for row in json.loads(readback.stdout)}
    for item in catalog["records"]:
        row = extracted[item["filename"]]
        if row.get("Title") != item["title"] or row.get("Description") != item["title"] or row.get("Subject") != item["keywords"]:
            raise MetadataError(f"Embedded XMP readback mismatch: {item['filename']}")
    report = {
        "platform": platform,
        "source_type": catalog["source_type"],
        "status": "draft_manual_review_required",
        "xmp_fields": ["dc:title", "dc:description", "dc:subject"],
        "images": results,
    }
    (output.parent / f"{output.name}_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--platform", choices=("adobe", "shutterstock"), required=True)
    args = parser.parse_args()
    try:
        report = embed(args.catalog, args.assets, args.output, args.platform)
    except MetadataError as exc:
        parser.exit(2, f"Metadata embedding blocked: {exc}\n")
    print(f"Embedded and verified XMP in {len(report['images'])} files: {args.output}")


if __name__ == "__main__":
    main()
