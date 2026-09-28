"""Copy prepared packages into one audited folder per requested image set."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile

try:
    from scripts.audit_output import audit
except ModuleNotFoundError:
    from audit_output import audit


def package_set(set_id: str, packages: list[Path], output: Path) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}", set_id):
        raise ValueError("Set ID must contain only letters, numbers, underscores or hyphens")
    if not packages or len({p.name.casefold() for p in packages}) != len(packages):
        raise ValueError("Provide packages with distinct directory names")
    for package in packages:
        if not package.is_dir() or package.is_symlink():
            raise ValueError(f"Invalid package directory: {package}")
        errors = audit(package.parent, package_names={package.name})
        if errors:
            raise ValueError("; ".join(errors))
    output.mkdir(parents=True, exist_ok=True)
    destination = output / set_id
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite {destination}")
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        pending = Path(temp) / destination.name
        pending.mkdir()
        for package in packages:
            target = pending / package.name
            shutil.copytree(package, target)
            for source in package.rglob("*"):
                if source.is_file():
                    copied = target / source.relative_to(package)
                    if hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(copied.read_bytes()).digest():
                        raise ValueError(f"Copy checksum mismatch: {source}")
        (pending / "set_manifest.json").write_text(json.dumps({
            "set_id": set_id, "packages": [package.name for package in packages],
        }, indent=2) + "\n", encoding="utf-8")
        errors = audit(Path(temp), set_only=True)
        if errors:
            raise ValueError("; ".join(errors))
        # Windows rename refuses an existing destination; check again before publishing.
        if destination.exists():
            raise FileExistsError(f"Refusing to overwrite {destination}")
        pending.rename(destination)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set-id", required=True)
    parser.add_argument("--packages", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[1] / "output")
    args = parser.parse_args()
    print(package_set(args.set_id, args.packages, args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
