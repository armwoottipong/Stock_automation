"""Tests for cull_and_prepare_metadata script."""

import json
from pathlib import Path
from unittest.mock import patch

from scripts.cull_and_prepare_metadata import run_cull_and_prepare_metadata


def test_run_cull_and_prepare_metadata(tmp_path):
    staging_dir = tmp_path / "staging_test"
    raw_dir = staging_dir / "raw_1024"
    raw_dir.mkdir(parents=True)

    # Create 2 fake raw images
    (raw_dir / "apple_01.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10)
    (raw_dir / "apple_02.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10)

    # Mock metadata gen
    fake_meta = {
        "title": "Fresh Sweet Apple on White Background",
        "category": 3,
        "keywords": ["apple", "red", "fruit", "white background", "isolated"],
    }
    # Mock dual inspect: apple_01 passes, apple_02 fails
    fake_dual_pass = {
        "pass": True,
        "primary_model": {"model": "m1", "pass": True, "confidence": 0.9, "summary": "ok"},
        "secondary_model": {"model": "m2", "pass": True, "confidence": 0.9, "summary": "ok"},
        "defects_detected": [],
        "rejection_reasons": [],
    }
    fake_dual_fail = {
        "pass": False,
        "primary_model": {"model": "m1", "pass": False, "confidence": 0.9, "summary": "bad"},
        "secondary_model": {"model": "m2", "pass": False, "confidence": 0.9, "summary": "bad"},
        "defects_detected": ["blur"],
        "rejection_reasons": ["Blury image"],
    }

    with patch("scripts.cull_and_prepare_metadata.generate_stock_metadata", return_value=fake_meta), \
         patch("scripts.cull_and_prepare_metadata.dual_inspect_candidate", side_effect=[fake_dual_pass, fake_dual_fail]), \
         patch("time.sleep"):

        summary = run_cull_and_prepare_metadata(staging_dir, pause_seconds=0)

        assert summary["total_evaluated"] == 2
        assert summary["passed_count"] == 1
        assert summary["rejected_count"] == 1
        assert "apple_01" in summary["passed_items"]
        assert "apple_02" in summary["rejected_items"]

        # Check raw_1024 only has passed apple_01
        assert (raw_dir / "apple_01.png").exists()
        assert not (raw_dir / "apple_02.png").exists()

        # Check rejected folder has apple_02
        assert (staging_dir / "rejected_raw" / "apple_02.png").exists()

        # Check draft_metadata.json
        draft_meta = json.loads((staging_dir / "draft_metadata.json").read_text(encoding="utf-8"))
        assert "apple_01" in draft_meta
        assert draft_meta["apple_01"]["title"] == "Fresh Sweet Apple on White Background"

        # Check culling_report.json
        report = json.loads((staging_dir / "culling_report.json").read_text(encoding="utf-8"))
        assert report["apple_01"]["pass"] is True
        assert report["apple_02"]["pass"] is False
