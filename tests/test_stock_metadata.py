import csv
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from ai_image_automation.stock_metadata import MetadataError, export_csv


def fixture_catalog(source_type="camera_photo", filename="apple.jpg"):
    return {
        "source_type": source_type,
        "language": "en",
        "records": [{
            "filename": filename,
            "title": "Whole red apple isolated on white background",
            "keywords": ["apple", "red", "whole", "fruit", "isolated", "white background", "food"],
            "shutterstock_category": "Food and drink",
        }],
    }


def test_shutterstock_rejects_generative_origin_even_with_neutral_metadata():
    with pytest.raises(MetadataError, match="does not accept"):
        export_csv(fixture_catalog("generative_ai"), "shutterstock")


def test_both_csv_schemas_for_camera_photo(tmp_path: Path):
    (tmp_path / "apple.jpg").write_bytes(b"fixture")
    catalog = fixture_catalog()
    adobe = list(csv.DictReader(io.StringIO(export_csv(catalog, "adobe", tmp_path))))
    shutter = list(csv.DictReader(io.StringIO(export_csv(catalog, "shutterstock", tmp_path))))
    assert adobe[0]["Filename"] == shutter[0]["Filename"] == "apple.jpg"
    assert adobe[0]["Title"] == shutter[0]["Description"]
    assert shutter[0]["Categories"] == "Food and drink"


def test_asset_and_metadata_guards(tmp_path: Path):
    catalog = fixture_catalog()
    with pytest.raises(MetadataError, match="Missing asset"):
        export_csv(catalog, "adobe", tmp_path)
    catalog["records"][0]["keywords"].append("APPLE")
    with pytest.raises(MetadataError, match="Duplicate keyword"):
        export_csv(catalog, "adobe")


def test_fruit_catalog_is_adobe_only():
    path = Path("staging/fruit_isolates_2026-09-26/metadata/catalog.json")
    if not path.is_file():
        pytest.skip("Local generated fruit set not present")
    catalog = json.loads(path.read_text(encoding="utf-8"))
    assert len(catalog["records"]) == 25
    assert len(list(csv.DictReader(io.StringIO(export_csv(catalog, "adobe", path.parent.parent / "cutout"))))) == 25
    with pytest.raises(MetadataError, match="does not accept"):
        export_csv(catalog, "shutterstock", path.parent.parent / "cutout")


def test_embedded_xmp_roundtrip_preserves_pixels(tmp_path: Path):
    if shutil.which("exiftool") is None:
        pytest.skip("ExifTool not installed")
    assets = tmp_path / "assets"
    assets.mkdir()
    Image.new("RGB", (5, 5), "red").save(assets / "apple.jpg")
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(fixture_catalog()), encoding="utf-8")
    output = tmp_path / "embedded"
    result = subprocess.run([
        sys.executable, "scripts/embed_stock_metadata.py", "--catalog", str(catalog_path),
        "--assets", str(assets), "--output", str(output), "--platform", "adobe",
    ], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert Image.open(assets / "apple.jpg").tobytes() == Image.open(output / "apple.jpg").tobytes()
    report = json.loads((tmp_path / "embedded_report.json").read_text(encoding="utf-8"))
    assert len(report["images"]) == 1
    assert report["xmp_fields"] == ["dc:title", "dc:description", "dc:subject"]


def test_embedded_export_blocks_ai_shutterstock_before_writing(tmp_path: Path):
    catalog_path = tmp_path / "catalog.json"
    catalog_path.write_text(json.dumps(fixture_catalog("generative_ai")), encoding="utf-8")
    result = subprocess.run([
        sys.executable, "scripts/embed_stock_metadata.py", "--catalog", str(catalog_path),
        "--assets", str(tmp_path), "--output", str(tmp_path / "embedded"),
        "--platform", "shutterstock",
    ], capture_output=True, text=True)
    assert result.returncode != 0
    assert "does not accept" in result.stderr
    assert not (tmp_path / "embedded").exists()
