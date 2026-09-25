"""Deterministic structural QC for generated image files."""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError


@dataclass(frozen=True)
class QCResult:
    passed: bool
    issues: tuple[str, ...]


def check_generated_image(path: Path, *, width: int, height: int) -> QCResult:
    issues: list[str] = []
    if not path.is_file() or path.stat().st_size == 0:
        return QCResult(False, ("missing_or_empty_file",))
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            if image.size != (width, height):
                issues.append("wrong_dimensions")
            extrema = image.convert("RGB").getextrema()
            if all(low == high for low, high in extrema):
                issues.append("blank_output")
    except (UnidentifiedImageError, OSError, ValueError):
        issues.append("corrupt_image")
    return QCResult(not issues, tuple(issues))
