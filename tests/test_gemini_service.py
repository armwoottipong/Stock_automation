"""Unit tests for gemini_service module."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import urllib.error

import pytest

from ai_image_automation.gemini_service import (
    call_gemini_api,
    dual_inspect_candidate,
    extract_candidate_text,
    generate_stock_metadata,
    inspect_image_candidate,
    load_gemini_api_key,
)


def test_load_gemini_api_key_from_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test_key_123")
    assert load_gemini_api_key() == "test_key_123"


def test_load_gemini_api_key_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GEMINI_API_KEY not found"):
        load_gemini_api_key(root=tmp_path)


def test_call_gemini_api_success():
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({
        "candidates": [{"content": {"parts": [{"text": '{"result": "ok"}'}]}}]
    }).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = call_gemini_api("test-model", [{"parts": [{"text": "hi"}]}], api_key="dummy_key")
        assert "candidates" in res
        text = extract_candidate_text(res)
        assert text == '{"result": "ok"}'


def test_call_gemini_api_retry_on_429():
    err_429 = urllib.error.HTTPError("http://example.com", 429, "Too Many Requests", {}, None)
    mock_success = MagicMock()
    mock_success.read.return_value = json.dumps({"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}).encode("utf-8")
    mock_success.__enter__.return_value = mock_success

    with patch("urllib.request.urlopen", side_effect=[err_429, mock_success]), patch("time.sleep") as mock_sleep:
        res = call_gemini_api("test-model", [{"parts": [{"text": "hi"}]}], api_key="dummy_key", retry_delay_seconds=0.01)
        assert extract_candidate_text(res) == "ok"
        assert mock_sleep.called


def test_generate_stock_metadata():
    mock_resp = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "title": "Fresh Red Apple on White Background",
                                "category": 3,
                                "keywords": ["apple", "red", "isolated", "fresh fruit", "ai-generated image"]
                            })
                        }
                    ]
                }
            }
        ]
    }
    with patch("ai_image_automation.gemini_service.call_gemini_api", return_value=mock_resp):
        meta = generate_stock_metadata("ripe red apple", api_key="dummy")
        assert meta["title"] == "Fresh Red Apple on White Background"
        assert "apple" in meta["keywords"]
        assert "white background" in meta["keywords"]
        # Must strip AI-generated tag
        assert "ai-generated image" not in meta["keywords"]


def test_inspect_image_candidate(tmp_path):
    img_file = tmp_path / "test.jpg"
    img_file.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 20)

    mock_resp = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "pass": True,
                                "confidence_score": 0.98,
                                "defects_detected": [],
                                "rejection_reasons": [],
                                "summary": "Crisp and clean isolated stock photo."
                            })
                        }
                    ]
                }
            }
        ]
    }
    with patch("ai_image_automation.gemini_service.call_gemini_api", return_value=mock_resp):
        report = inspect_image_candidate(img_file, "clean apple", api_key="dummy")
        assert report["pass"] is True
        assert report["confidence_score"] == 0.98


def test_dual_inspect_candidate(tmp_path):
    img_file = tmp_path / "test.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)

    pass_result = {
        "pass": True,
        "confidence_score": 0.95,
        "defects_detected": [],
        "rejection_reasons": [],
        "summary": "Passed inspection"
    }
    fail_result = {
        "pass": False,
        "confidence_score": 0.90,
        "defects_detected": ["blur"],
        "rejection_reasons": ["Out of focus"],
        "summary": "Failed inspection"
    }

    # Case 1: Both pass
    with patch("ai_image_automation.gemini_service.inspect_image_candidate", side_effect=[pass_result, pass_result]), patch("time.sleep"):
        res = dual_inspect_candidate(img_file, "test", api_key="dummy")
        assert res["pass"] is True

    # Case 2: One fails -> consensus fails
    with patch("ai_image_automation.gemini_service.inspect_image_candidate", side_effect=[pass_result, fail_result]), patch("time.sleep"):
        res = dual_inspect_candidate(img_file, "test", api_key="dummy")
        assert res["pass"] is False
        assert "blur" in res["defects_detected"]
