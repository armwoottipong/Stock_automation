"""Download only the two approved Phase 5 publisher snapshots and verify weights."""

from __future__ import annotations

import hashlib
from pathlib import Path

from huggingface_hub import snapshot_download


ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "vendor" / "background_models"
CANDIDATES = (
    (
        "birefnet-dis",
        "ZhengPeng7/BiRefNet",
        "6a62b7dcfa18a3829087877fb16c8006831e4220",
        "9ab37426bf4de0567af6b5d21b16151357149139362e6e8992021b8ce356a154",
        ["model.safetensors", "config.json", "birefnet.py", "BiRefNet_config.py", "requirements.txt", "README.md"],
    ),
    (
        "ben2-base",
        "PramaLLC/BEN2",
        "19d0d22912541ae3178d10682640616c7287957b",
        "ea8b7907176a09667c86343dc7d00de6a6d871076cb90bb5f753618fd6fb3ebb",
        ["model.safetensors", "BEN2.py", "config.json", "requirements.txt", "README.md"],
    ),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    for name, repo_id, revision, expected, files in CANDIDATES:
        destination = DEST / name
        snapshot_download(
            repo_id=repo_id,
            revision=revision,
            local_dir=destination,
            allow_patterns=files,
        )
        weight = destination / "model.safetensors"
        actual = sha256(weight)
        if actual != expected:
            raise RuntimeError(f"{name} SHA-256 mismatch: {actual}")
        print(f"{name}: {weight.stat().st_size} bytes SHA-256 {actual}")


if __name__ == "__main__":
    main()
