"""Contributor CSV metadata with provenance and platform eligibility checks."""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path


class MetadataError(ValueError):
    pass


ADOBE_HEADERS = ("Filename", "Title", "Keywords", "Category", "Releases")
SHUTTERSTOCK_HEADERS = ("Filename", "Description", "Keywords", "Categories")
FORBIDDEN_PUBLIC_TERMS = re.compile(r"\b(?:ai[ -]?generated|generative ai|artificial intelligence)\b", re.I)


def validate_catalog(catalog: dict, platform: str, asset_dir: Path | None = None) -> None:
    if platform not in {"adobe", "shutterstock"}:
        raise MetadataError("Unknown platform")
    if catalog.get("source_type") not in {"generative_ai", "camera_photo"}:
        raise MetadataError("Explicit source_type is required")
    if platform == "shutterstock" and catalog["source_type"] == "generative_ai":
        raise MetadataError("Shutterstock does not accept contributor AI-generated content")
    if catalog.get("language") != "en":
        raise MetadataError("This exporter requires English metadata")
    records = catalog.get("records")
    if not isinstance(records, list) or not records:
        raise MetadataError("Nonempty records list is required")
    seen_files: set[str] = set()
    for record in records:
        filename = record.get("filename", "")
        title = record.get("title", "")
        keywords = record.get("keywords", [])
        if not isinstance(filename, str) or Path(filename).name != filename or not filename.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")):
            raise MetadataError(f"Invalid filename: {filename}")
        if filename.casefold() in seen_files:
            raise MetadataError(f"Duplicate filename: {filename}")
        seen_files.add(filename.casefold())
        if asset_dir is not None and not (asset_dir / filename).is_file():
            raise MetadataError(f"Missing asset: {filename}")
        if not isinstance(title, str) or len(title.split()) < 5 or FORBIDDEN_PUBLIC_TERMS.search(title):
            raise MetadataError(f"Invalid or misleading title: {filename}")
        if not isinstance(keywords, list) or not 7 <= len(keywords) <= 49:
            raise MetadataError(f"Expected 7–49 keywords: {filename}")
        if any(not isinstance(k, str) or not k.strip() or "," in k or FORBIDDEN_PUBLIC_TERMS.search(k) for k in keywords):
            raise MetadataError(f"Invalid keyword: {filename}")
        if len({k.casefold().strip() for k in keywords}) != len(keywords):
            raise MetadataError(f"Duplicate keyword: {filename}")
        if platform == "adobe":
            if len(filename) > 30 or len(title) > 70 or "," in title or re.search(r"[^\w\s-]", title):
                raise MetadataError(f"Adobe filename/title limit: {filename}")
        else:
            # Shutterstock's submission UI documents 150 characters although
            # its policy article gives a larger general title limit.
            if len(title) > 150 or filename.lower().endswith(".png"):
                raise MetadataError(f"Shutterstock title or file format: {filename}")
            if record.get("shutterstock_category") not in {"Food and drink"}:
                raise MetadataError(f"Shutterstock category required: {filename}")


def export_csv(catalog: dict, platform: str, asset_dir: Path | None = None) -> str:
    validate_catalog(catalog, platform, asset_dir)
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(ADOBE_HEADERS if platform == "adobe" else SHUTTERSTOCK_HEADERS)
    for item in catalog["records"]:
        common = [item["filename"], item["title"], ", ".join(item["keywords"])]
        if platform == "adobe":
            writer.writerow([*common, item.get("adobe_category", ""), ""])
        else:
            writer.writerow([*common, item["shutterstock_category"]])
    csv_text = buffer.getvalue()
    if platform == "adobe" and (len(catalog["records"]) > 5000 or len(csv_text.encode("utf-8")) > 1_000_000):
        raise MetadataError("Adobe CSV exceeds row or byte limit")
    return csv_text


def load_catalog(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
