"""Phase 5 local candidate benchmark; no production background default is implied."""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import sys
import time
import types
from importlib import metadata
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageOps
from safetensors.torch import load_file
from torchvision import transforms


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK = ROOT / "benchmarks" / "background"
MODELS = ROOT / "vendor" / "background_models"


def load_model(name: str):
    if name == "birefnet-dis":
        path = MODELS / name
        package = types.ModuleType("phase5_birefnet")
        package.__path__ = [str(path)]
        sys.modules[package.__name__] = package
        source = importlib.import_module(".birefnet", package.__name__)
        model = source.BiRefNet()
        model.load_state_dict(load_file(path / "model.safetensors"), strict=True)
        return model.eval().to("cuda").half()

    if name == "ben2-base":
        path = MODELS / name
        spec = importlib.util.spec_from_file_location("publisher_ben2", path / "BEN2.py")
        if spec is None or spec.loader is None:
            raise RuntimeError("Cannot load pinned BEN2 Base source")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        model = module.BEN_Base()
        model.load_state_dict(load_file(path / "model.safetensors"), strict=True)
        return model.eval().to("cuda")

    raise ValueError(name)


def infer(name: str, model, image: Image.Image) -> Image.Image:
    rgb = ImageOps.exif_transpose(image).convert("RGB")
    if name == "ben2-base":
        return model.inference(rgb, refine_foreground=False).convert("RGBA")

    transform = transforms.Compose(
        [
            transforms.Resize((1024, 1024)),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
        ]
    )
    tensor = transform(rgb).unsqueeze(0).to("cuda").half()
    with torch.inference_mode():
        prediction = model(tensor)[-1].sigmoid()[0, 0].float().cpu()
    mask = transforms.ToPILImage()(prediction).resize(rgb.size, Image.Resampling.BILINEAR)
    rgba = rgb.convert("RGBA")
    rgba.putalpha(mask)
    return rgba


def summarize(image: Image.Image) -> dict:
    alpha = np.asarray(image.getchannel("A"), dtype=np.uint8)
    foreground = alpha >= 128
    ys, xs = np.nonzero(foreground)
    bounds = None if not len(xs) else [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
    return {
        "size": list(image.size),
        "alpha_min": int(alpha.min()),
        "alpha_max": int(alpha.max()),
        "transparent_fraction": round(float(np.mean(alpha == 0)), 6),
        "opaque_fraction": round(float(np.mean(alpha == 255)), 6),
        "partial_fraction": round(float(np.mean((alpha > 0) & (alpha < 255))), 6),
        "foreground_bounds_128": bounds,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=("birefnet-dis", "ben2-base"), required=True)
    parser.add_argument("--manifest", choices=("cases.json", "isolated_cases.json"), default="cases.json")
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for the Phase 5 VRAM benchmark")

    cases = json.loads((BENCHMARK / args.manifest).read_text(encoding="utf-8"))["cases"]
    missing = [case["input"] for case in cases if not (BENCHMARK / case["input"]).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing benchmark inputs: {missing}")

    started = time.perf_counter()
    model = load_model(args.model)
    torch.cuda.synchronize()
    load_seconds = time.perf_counter() - started
    run_info = {
        "model": args.model,
        "load_seconds": round(load_seconds, 3),
        "gpu": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "timm": metadata.version("timm"),
        "opencv_python_headless": metadata.version("opencv-python-headless"),
    }
    print(json.dumps(run_info), flush=True)
    output_dir = BENCHMARK / "output" / ("isolated" if args.manifest == "isolated_cases.json" else "scene") / args.model
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for case in cases:
        input_path = BENCHMARK / case["input"]
        with Image.open(input_path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
        torch.cuda.reset_peak_memory_stats()
        started = time.perf_counter()
        try:
            output = infer(args.model, model, image)
            torch.cuda.synchronize()
            seconds = time.perf_counter() - started
            if output.size != image.size:
                raise ValueError(f"Output dimensions changed: {image.size} -> {output.size}")
            destination = output_dir / f"{case['id']}.png"
            output.save(destination)
            result = {
                "model": args.model,
                "case_id": case["id"],
                "category": case["category"],
                "seconds": round(seconds, 3),
                "peak_allocated_gib": round(torch.cuda.max_memory_allocated() / 2**30, 3),
                "peak_reserved_gib": round(torch.cuda.max_memory_reserved() / 2**30, 3),
                "output": str(destination.relative_to(ROOT)),
                **summarize(output),
            }
        except Exception as exc:
            result = {
                "model": args.model,
                "case_id": case["id"],
                "category": case["category"],
                "error": f"{type(exc).__name__}: {exc}",
            }
            torch.cuda.empty_cache()
        results.append(result)
        print(json.dumps(result), flush=True)
    (output_dir / "results.json").write_text(
        json.dumps({"run": run_info, "cases": results}, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
