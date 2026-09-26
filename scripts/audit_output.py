"""Reject drafts and untracked files from the final stock output directory."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_CHECKS = ("visual_review", "metadata", "technical", "rights")
DELIVERABLE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".zip"}


def audit(root: Path) -> list[str]:
    errors: list[str] = []
    if not root.is_dir():
        return [f"Output directory is missing: {root}"]
    for entry in sorted(root.iterdir()):
        if entry.name == ".gitkeep" and entry.is_file():
            continue
        if entry.is_symlink():
            errors.append(f"Symlink in output: {entry.name}")
            continue
        if not entry.is_dir():
            errors.append(f"Loose file in output: {entry.name}")
            continue
        manifest_path = entry / "submission_manifest.json"
        if not manifest_path.is_file():
            errors.append(f"Missing submission manifest: {entry.name}")
            continue
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            errors.append(f"Invalid submission manifest: {entry.name}")
            continue
        if not isinstance(manifest, dict):
            errors.append(f"Invalid submission manifest: {entry.name}")
            continue
        if manifest.get("status") != "ready_to_submit":
            errors.append(f"Package is not approved: {entry.name}")
        platform = manifest.get("platform")
        origin = manifest.get("source_type")
        if platform not in {"adobe_stock", "shutterstock"} or origin not in {"generative_ai", "camera_photo"}:
            errors.append(f"Invalid platform or source type: {entry.name}")
        if platform == "shutterstock" and origin == "generative_ai":
            errors.append(f"AI-generated package blocked for Shutterstock: {entry.name}")
        if platform == "adobe_stock" and origin == "generative_ai" and manifest.get("adobe_ai_disclosure_required") is not True:
            errors.append(f"Adobe AI disclosure step missing: {entry.name}")
        checks = manifest.get("checks")
        if not isinstance(checks, dict) or any(checks.get(name) is not True for name in REQUIRED_CHECKS):
            errors.append(f"Required reviews incomplete: {entry.name}")
        assets = manifest.get("assets")
        if not isinstance(assets, list) or not assets or any(not isinstance(name, str) for name in assets):
            errors.append(f"No valid asset list: {entry.name}")
            continue
        declared: set[str] = set()
        package_root = entry.resolve()
        for name in assets:
            path = entry / name
            if not path.resolve().is_relative_to(package_root) or path.name in {"submission_manifest.json", "README.md"}:
                errors.append(f"Invalid asset path: {entry.name}/{name}")
                continue
            if name in declared:
                errors.append(f"Duplicate asset: {entry.name}/{name}")
            declared.add(name)
            if not path.is_file():
                errors.append(f"Missing asset: {entry.name}/{name}")
        package_entries = list(entry.rglob("*"))
        if any(p.is_symlink() for p in package_entries):
            errors.append(f"Symlink in package: {entry.name}")
        actual = {p.relative_to(entry).as_posix() for p in package_entries if p.is_file() and p.name not in {"submission_manifest.json", "README.md"}}
        if actual != {name.replace("\\", "/") for name in declared}:
            errors.append(f"Unlisted or missing files in package: {entry.name}")
        if not any(Path(name).suffix.lower() in DELIVERABLE_SUFFIXES for name in declared):
            errors.append(f"No image or archive deliverable: {entry.name}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "output")
    args = parser.parse_args()
    errors = audit(args.output)
    if errors:
        for message in errors:
            print(f"FAIL: {message}")
        return 1
    print("PASS: output contains only approved submission packages or is empty")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
