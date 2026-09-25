"""Pinned BiRefNet inference for the Phase 6 opaque-object path."""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

from PIL import Image, ImageOps


def load_birefnet(checkpoint: Path):
    import torch
    from safetensors.torch import load_file

    package = types.ModuleType("phase6_birefnet")
    package.__path__ = [str(checkpoint.parent)]
    sys.modules[package.__name__] = package
    source = importlib.import_module(".birefnet", package.__name__)
    model = source.BiRefNet()
    model.load_state_dict(load_file(checkpoint), strict=True)
    return model.eval().to("cuda").half()


def cutout_birefnet(model, image: Image.Image) -> Image.Image:
    import torch
    from torchvision import transforms

    rgb = ImageOps.exif_transpose(image).convert("RGB")
    transform = transforms.Compose([
        transforms.Resize((1024, 1024)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])
    tensor = transform(rgb).unsqueeze(0).to("cuda").half()
    with torch.inference_mode():
        prediction = model(tensor)[-1].sigmoid()[0, 0].float().cpu()
    mask = transforms.ToPILImage()(prediction).resize(rgb.size, Image.Resampling.BILINEAR)
    output = rgb.convert("RGBA")
    output.putalpha(mask)
    return output
