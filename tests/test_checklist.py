import json
from pathlib import Path

from scripts.update_submission_checklist import build_checklist_html, scan_output_sets, update_checklist


def test_scan_output_sets_empty(tmp_path: Path):
    assert scan_output_sets(tmp_path) == []


def test_scan_output_sets_extracts_correct_fields(tmp_path: Path):
    set_dir = tmp_path / "mock_fruits_2026-10-02_001"
    set_dir.mkdir()
    
    (set_dir / "set_manifest.json").write_text(json.dumps({
        "set_id": "mock_fruits_2026-10-02_001",
        "packages": ["adobe_stock", "metadata", "white_jpeg_companion"]
    }))
    
    meta_dir = set_dir / "metadata"
    meta_dir.mkdir()
    (meta_dir / "catalog.json").write_text(json.dumps({
        "records": [
            {"title": "Crisp Fuji Apple Isolated on White", "keywords": ["apple", "fruit"]}
        ]
    }))
    (meta_dir / "adobe_stock.csv").write_text("Filename,Title\nphoto.png,Apple\n")
    
    img_dir = set_dir / "adobe_stock"
    img_dir.mkdir()
    (img_dir / "photo.png").write_bytes(b"mock")
    
    (set_dir / "white_jpeg_companion").mkdir()

    scanned = scan_output_sets(tmp_path)
    assert len(scanned) == 1
    item = scanned[0]
    assert item["id"] == "mock_fruits_2026-10-02_001"
    assert item["date"] == "2026-10-02"
    assert item["title"] == "Crisp Fuji Apple Isolated on White"
    assert item["image_count"] == 1
    assert "adobe_stock" in item["packages"]
    assert item["has_csv"] is True
    assert item["has_white_jpg"] is True
    assert item["has_transparent_png"] is True


def test_build_checklist_html_contains_required_agencies_and_storage():
    projects = [
        {
            "id": "test_set_001",
            "date": "2026-10-02",
            "title": "Test Set",
            "image_count": 50,
            "packages": ["adobe_stock"],
            "has_csv": True,
            "has_white_jpg": False,
            "has_transparent_png": True,
            "has_contact_sheet": False,
            "keywords_sample": ["test"],
        }
    ]
    html = build_checklist_html(projects)
    assert "stock_submission_checklist_v1" in html
    assert "localStorage" in html
    assert "Adobe Stock" in html
    assert "Shutterstock" in html
    assert "123RF" in html
    assert "Others" in html
    assert "test_set_001" in html


def test_update_checklist_generates_json_and_html(tmp_path: Path):
    out_dir = tmp_path / "output"
    out_dir.mkdir()
    docs_dir = tmp_path / "docs"
    
    # Create sample set
    s_dir = out_dir / "test_set_2026-10-02_001"
    s_dir.mkdir()
    (s_dir / "set_manifest.json").write_text(json.dumps({
        "set_id": "test_set_2026-10-02_001",
        "packages": ["adobe_stock"]
    }))
    as_dir = s_dir / "adobe_stock"
    as_dir.mkdir()
    (as_dir / "sample.png").write_bytes(b"data")

    json_path, html_path = update_checklist(output_dir=out_dir, docs_dir=docs_dir, verbose=False)
    
    assert json_path.is_file()
    assert html_path.is_file()
    
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(loaded) == 1
    assert loaded[0]["id"] == "test_set_2026-10-02_001"
    
    html_content = html_path.read_text(encoding="utf-8")
    assert "test_set_2026-10-02_001" in html_content
