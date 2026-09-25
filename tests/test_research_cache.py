import shutil
from datetime import date
from pathlib import Path

import pytest

from ai_image_automation.research_cache import load_context, lookup, upsert
from ai_image_automation.registry import ResearchCache, ResearchEntry


ROOT = Path(__file__).resolve().parents[1]


def test_shipped_research_is_fresh_and_uses_registry_license_evidence():
    context = load_context(ROOT / "data")
    result = lookup(context, "remove_background", "opaque_isolate", as_of=date(2026, 9, 25))
    assert result.status == "fresh"
    assert result.usable_model_id == "birefnet-dis"
    glass = lookup(context, "remove_background", "glass_isolate", as_of=date(2026, 9, 25))
    assert glass.status == "fresh"
    assert glass.entry.outcome == "manual_review"
    assert glass.usable_model_id is None
    assert lookup(context, "generate", "unknown", as_of=date(2026, 9, 25)).status == "missing"


def test_expired_entry_never_returns_a_usable_model():
    context = load_context(ROOT / "data")
    result = lookup(context, "remove_background", "opaque_isolate", as_of=date(2026, 10, 26))
    assert result.status == "stale"
    assert result.usable_model_id is None


def test_changed_license_invalidates_cached_selection():
    context = load_context(ROOT / "data")
    context.licenses.records = [
        record for record in context.licenses.records if record.resource_id != "birefnet-dis"
    ]
    result = lookup(context, "remove_background", "opaque_isolate", as_of=date(2026, 9, 25))
    assert result.status == "registry_invalid"
    assert result.usable_model_id is None


def test_upsert_replaces_one_key_and_preserves_other_entries(tmp_path: Path):
    data_dir = tmp_path / "data"
    shutil.copytree(ROOT / "data", data_dir)
    old = load_context(data_dir).cache
    entry = next(item for item in old.entries if item.subject_type == "glass_isolate")
    updated_entry = entry.model_copy(update={"summary": "Reviewed: glass still needs a manual route."})
    updated = upsert(data_dir, updated_entry, as_of=date(2026, 9, 25))
    assert len(updated.entries) == len(old.entries)
    assert next(item for item in updated.entries if item.subject_type == "glass_isolate").summary == updated_entry.summary
    assert ResearchCache.model_validate_json((data_dir / "research_cache.json").read_text(encoding="utf-8")) == updated


def test_cache_rejects_duplicate_key_and_unbounded_expiry():
    entry = ResearchEntry(
        task="upscale", subject_type="pixel_2x", candidate_ids=["realesrgan-x2plus"],
        sources=["https://example.org/model"], outcome="manual_review",
        verified_at=date(2026, 9, 25), expires_at=date(2026, 10, 25),
    )
    with pytest.raises(ValueError, match="duplicate research cache key"):
        ResearchCache(entries=[entry, entry])
    with pytest.raises(ValueError, match="within 30 days"):
        ResearchEntry.model_validate({**entry.model_dump(), "expires_at": date(2027, 1, 1)})
