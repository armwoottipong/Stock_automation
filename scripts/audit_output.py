"""Audit packaged stock files and deterministic delivery checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_CHECKS = ("metadata", "technical", "rights")
DELIVERABLE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}


def audit_set(path: Path) -> list[str]:
    """Validate one delivery folder and its platform-specific packages."""
    if any(entry.is_symlink() for entry in path.iterdir()):
        return [f"Symlink in set: {path.name}"]
    try:
        manifest = json.loads((path / "set_manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [f"Invalid set manifest: {path.name}"]
    if not isinstance(manifest, dict) or manifest.get("set_id") != path.name:
        return [f"Invalid set identity: {path.name}"]
    packages = manifest.get("packages")
    if (not isinstance(packages, list) or not packages
            or any(not isinstance(name, str) or name in {"", ".", ".."}
                   or any(char in name for char in "/\\:") for name in packages)
            or len({name.casefold() for name in packages}) != len(packages)):
        return [f"Invalid package list: {path.name}"]
    if any(key in manifest for key in ("status", "visual_review", "visual_review_owner", "checks")):
        return [f"Set manifest must only describe delivery inventory: {path.name}"]
    actual = {entry.name for entry in path.iterdir()}
    if actual != set(packages) | {"set_manifest.json"}:
        return [f"Unlisted or missing package in set: {path.name}"]
    if any(not (path / name / "submission_manifest.json").is_file() for name in packages):
        return [f"Missing internal submission manifest: {path.name}"]
    return [f"{path.name}: {error}" for error in audit(path, package_names=set(packages))]


def audit(root: Path, *, set_only: bool = False, package_names: set[str] | None = None) -> list[str]:
    errors: list[str] = []
    if not root.is_dir():
        return [f"Output directory is missing: {root}"]
    for entry in sorted(root.iterdir()):
        if package_names is not None and entry.name not in package_names:
            continue
        if entry.name == ".gitkeep" and entry.is_file():
            continue
        if entry.is_symlink():
            errors.append(f"Symlink in output: {entry.name}")
            continue
        if not entry.is_dir():
            errors.append(f"Loose file in output: {entry.name}")
            continue
        if (entry / "set_manifest.json").is_file():
            errors.extend(audit_set(entry))
            continue
        if set_only:
            errors.append(f"Missing set manifest (one folder per set required): {entry.name}")
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
        if any(name in manifest for name in (
            "status", "visual_review_owner", "visual_reviewer", "user_cull_after_delivery",
        )):
            errors.append(f"Review-status field is not part of a production package: {entry.name}")
        platform = manifest.get("platform")
        origin = manifest.get("source_type")
        if platform not in {"adobe_stock", "shutterstock", "local_delivery"} or origin not in {"generative_ai", "camera_photo"}:
            errors.append(f"Invalid platform or source type: {entry.name}")
        if platform == "local_delivery" and manifest.get("package_purpose") != "white_png_companion":
            errors.append(f"Invalid local delivery purpose: {entry.name}")
        if platform == "shutterstock" and origin == "generative_ai":
            errors.append(f"AI-generated package blocked for Shutterstock: {entry.name}")
        if platform == "adobe_stock" and origin == "generative_ai" and manifest.get("adobe_ai_disclosure_required") is not True:
            errors.append(f"Adobe AI disclosure step missing: {entry.name}")
        checks = manifest.get("checks")
        if not isinstance(checks, dict) or any(checks.get(name) is not True for name in REQUIRED_CHECKS):
            errors.append(f"Required checks incomplete: {entry.name}")
        if isinstance(checks, dict) and "visual_review" in checks:
            errors.append(f"Visual-review check is not part of a production package: {entry.name}")
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
            errors.append(f"No image deliverable: {entry.name}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "output")
    args = parser.parse_args()
    errors = audit(args.output, set_only=True)
    if errors:
        for message in errors:
            print(f"FAIL: {message}")
        return 1
    print("PASS: output contains only audited set folders or is empty")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
