"""Install only the pinned FLUX.2 Klein trial files after provenance review."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from huggingface_hub import hf_hub_download


ROOT = Path(__file__).resolve().parents[1]
MODELS = ROOT / "vendor" / "ComfyUI" / "models"
DOWNLOADS = ROOT / "vendor" / "flux2_klein_downloads"
FILES = (
    (
        "black-forest-labs/FLUX.2-klein-4b-fp8",
        "5b4408e59397a4a37ccb46afe426d8ed86379441",
        "flux-2-klein-4b-fp8.safetensors",
        "diffusion_models/flux-2-klein-4b-fp8.safetensors",
        4_070_624_520,
        "97ed34fe0567e436200f2faee3939b88f2b5d99f8af2a4dc16532c4245c0ccb6",
    ),
    (
        "Comfy-Org/vae-text-encorder-for-flux-klein-4b",
        "5f526678002e43af5551dadb73ce2e8c91b43afe",
        "split_files/text_encoders/qwen_3_4b_fp4_flux2.safetensors",
        "text_encoders/qwen_3_4b_fp4_flux2.safetensors",
        3_848_213_998,
        "3eab03a77adb0ee5304a4e677d5c10ac22f9049c1d7c894adca4f8bb39206ca8",
    ),
    (
        "Comfy-Org/vae-text-encorder-for-flux-klein-4b",
        "5f526678002e43af5551dadb73ce2e8c91b43afe",
        "split_files/vae/flux2-vae.safetensors",
        "vae/flux2-vae.safetensors",
        336_211_292,
        "868fe7b343cc8f3a19dbcfcafbc3d5f888802be3f89bd81b65b3621a066ce8f3",
    ),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if not (ROOT / "vendor" / "ComfyUI" / "main.py").is_file():
        raise RuntimeError("Pinned ComfyUI installation is missing")
    MODELS.mkdir(parents=True, exist_ok=True)
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    if not MODELS.resolve().is_relative_to(ROOT.resolve()) or not DOWNLOADS.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError("Model paths must stay inside the project")
    missing_bytes = sum(size for _, _, _, name, size, digest in FILES if not (MODELS / name).is_file())
    free_bytes = shutil.disk_usage(ROOT).free
    if free_bytes < missing_bytes + 5 * 1024**3:
        raise RuntimeError(f"Insufficient disk space: {free_bytes} bytes free, {missing_bytes} bytes of weights missing")
    for repo, revision, filename, relative, size, digest in FILES:
        destination = MODELS / relative
        if destination.is_file():
            if destination.stat().st_size != size or sha256_file(destination) != digest:
                raise RuntimeError(f"Existing model file differs: {destination}")
            print(f"Verified existing {destination}", flush=True)
            continue
        source = Path(hf_hub_download(repo_id=repo, revision=revision, filename=filename, local_dir=DOWNLOADS))
        if source.stat().st_size != size or sha256_file(source) != digest:
            raise RuntimeError(f"Downloaded hash/size mismatch: {source}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.resolve().is_relative_to(MODELS.resolve()):
            raise RuntimeError(f"Destination outside model root: {destination}")
        shutil.move(str(source), str(destination))
        print(f"Installed and verified {destination}", flush=True)
    print("FLUX.2 Klein 4B FP8 trial files verified; benchmark and registry update remain required", flush=True)


if __name__ == "__main__":
    main()
