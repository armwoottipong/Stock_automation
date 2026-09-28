"""Audit packaged stock files and deterministic delivery checks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import stat
import tempfile
import zipfile


REQUIRED_CHECKS = ("metadata", "technical", "rights")
DELIVERABLE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".zip"}


def audit_archive(path: Path) -> list[str]:
    """Validate archive paths, CRCs and every contained platform package."""
    try:
        with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory() as temp:
            entries = archive.infolist()
            if not entries or len(entries) > 10000 or sum(e.file_size for e in entries) > 10 * 1024**3:
                return [f"Empty or oversized archive: {path.name}"]
            names: set[str] = set()
            for entry in entries:
                name = entry.filename
                parts = PurePosixPath(name).parts
                if (not parts or name.startswith("/") or "\\" in name or ":" in name
                        or ".." in parts or name.casefold() in names
                        or stat.S_ISLNK(entry.external_attr >> 16)):
                    return [f"Unsafe or duplicate archive path: {path.name}/{name}"]
                names.add(name.casefold())
                if not entry.is_dir() and len(parts) < 2:
                    return [f"Loose file inside archive: {path.name}/{name}"]
            bad = archive.testzip()
            if bad:
                return [f"Corrupt archive member: {path.name}/{bad}"]
            archive.extractall(temp)
            errors = audit(Path(temp))
            return [f"{path.name}: {error}" for error in errors]
    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as exc:
        return [f"Invalid archive: {path.name}: {exc}"]


def audit(root: Path, *, archive_only: bool = False, package_names: set[str] | None = None) -> list[str]:
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
        if entry.is_file() and entry.suffix.lower() == ".zip":
            errors.extend(audit_archive(entry))
            continue
        if not entry.is_dir():
            errors.append(f"Loose file in output: {entry.name}")
            continue
        if archive_only:
            errors.append(f"Unbundled package in output (one ZIP per set required): {entry.name}")
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
            errors.append(f"No image or archive deliverable: {entry.name}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "output")
    args = parser.parse_args()
    errors = audit(args.output, archive_only=True)
    if errors:
        for message in errors:
            print(f"FAIL: {message}")
        return 1
    print("PASS: output contains only audited set ZIPs or is empty")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
