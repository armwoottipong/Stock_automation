import csv
import io
import json
from pathlib import Path

import pytest

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
    path = Path("output/fruit_isolates_2026-09-26/metadata/catalog.json")
    if not path.is_file():
        pytest.skip("Local generated fruit set not present")
    catalog = json.loads(path.read_text(encoding="utf-8"))
    assert len(catalog["records"]) == 25
    assert len(list(csv.DictReader(io.StringIO(export_csv(catalog, "adobe", path.parent.parent / "cutout"))))) == 25
    with pytest.raises(MetadataError, match="does not accept"):
        export_csv(catalog, "shutterstock", path.parent.parent / "cutout")
