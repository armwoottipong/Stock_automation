"""Bundle prepared packages into one verified ZIP per requested image set."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import tempfile
import zipfile

try:
    from scripts.audit_output import audit, audit_archive
except ModuleNotFoundError:
    from audit_output import audit, audit_archive


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
    destination = output / f"{set_id}.zip"
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite {destination}")
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        pending = Path(temp) / destination.name
        with zipfile.ZipFile(pending, "w", compression=zipfile.ZIP_STORED) as archive:
            for package in packages:
                for file in sorted(package.rglob("*")):
                    if file.is_file():
                        archive.write(file, f"{package.name}/{file.relative_to(package).as_posix()}")
        errors = audit_archive(pending)
        if errors:
            raise ValueError("; ".join(errors))
        # Exclusive creation prevents an existing set from being overwritten.
        with pending.open("rb") as source, destination.open("xb") as target:
            import shutil
            shutil.copyfileobj(source, target)
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
