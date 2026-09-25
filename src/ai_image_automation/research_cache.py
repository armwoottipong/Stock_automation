"""Offline research lookup and reviewed cache updates for the control plane."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from ai_image_automation.registry import (
    LicenseRegistry, ModelRecord, ResearchCache, ResearchEntry, ToolRegistry, load_registry,
)


REGISTRY_FILES = (
    "background_registry.json", "controlnet_registry.json", "license_registry.json",
    "model_registry.json", "research_cache.json", "tool_registry.json", "upscaler_registry.json",
)


@dataclass(frozen=True)
class ResearchContext:
    cache: ResearchCache
    models: dict[str, ModelRecord]
    licenses: LicenseRegistry
    root: Path


@dataclass(frozen=True)
class LookupResult:
    status: Literal["fresh", "stale", "missing", "registry_invalid"]
    entry: ResearchEntry | None
    usable_model_id: str | None
    reason: str | None = None

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "entry": self.entry.model_dump(mode="json") if self.entry else None,
            "usable_model_id": self.usable_model_id,
            "reason": self.reason,
        }


def load_context(data_dir: Path) -> ResearchContext:
    """Validate every project registry before making a research decision."""
    for filename in REGISTRY_FILES:
        if not (data_dir / filename).is_file():
            raise FileNotFoundError(data_dir / filename)
    models: dict[str, ModelRecord] = {}
    for filename in (
        "background_registry.json", "controlnet_registry.json", "model_registry.json", "upscaler_registry.json",
    ):
        for record in load_registry(data_dir / filename).records:
            if record.id in models:
                raise ValueError(f"duplicate model id across registries: {record.id}")
            models[record.id] = record
    licenses = LicenseRegistry.model_validate_json((data_dir / "license_registry.json").read_text(encoding="utf-8"))
    ToolRegistry.model_validate_json((data_dir / "tool_registry.json").read_text(encoding="utf-8"))
    cache = ResearchCache.model_validate_json((data_dir / "research_cache.json").read_text(encoding="utf-8"))
    return ResearchContext(cache=cache, models=models, licenses=licenses, root=data_dir.resolve().parent)


def _registry_issue(entry: ResearchEntry, context: ResearchContext) -> str | None:
    missing = [identifier for identifier in entry.candidate_ids if identifier not in context.models]
    if missing:
        return f"unknown candidate IDs: {', '.join(missing)}"
    if entry.outcome != "selected":
        return None
    model = context.models[entry.selected_model_id or ""]
    if (entry.task not in model.tasks or model.commercial_use != "allowed" or not model.source
            or not model.license or not model.installed or not model.local_path):
        return "selected model is no longer commercially eligible for this task"
    if model.last_verified != entry.verified_at:
        return "selected model verification date does not match the research entry"
    evidence = [record for record in context.licenses.records if record.resource_id == model.id]
    if len(evidence) != 1 or evidence[0].commercial_use != "allowed" or evidence[0].license != model.license:
        return "selected model lacks matching commercial license evidence"
    if evidence[0].last_verified != entry.verified_at:
        return "license verification date does not match the research entry"
    if model.source not in entry.sources or evidence[0].source not in entry.sources:
        return "research entry lacks model or license source evidence"
    benchmark = (context.root / (entry.benchmark_path or "")).resolve()
    if not benchmark.is_relative_to(context.root) or not benchmark.is_file():
        return "selected model benchmark evidence is missing"
    return None


def lookup(
    context: ResearchContext, task: str, subject_type: str, *, as_of: date | None = None,
) -> LookupResult:
    today = as_of or date.today()
    entry = next(
        (item for item in context.cache.entries if item.task == task and item.subject_type == subject_type),
        None,
    )
    if entry is None:
        return LookupResult("missing", None, None, "no reviewed cache entry")
    if today < entry.verified_at or today > entry.expires_at:
        return LookupResult("stale", entry, None, "review or license evidence must be refreshed")
    issue = _registry_issue(entry, context)
    if issue:
        return LookupResult("registry_invalid", entry, None, issue)
    return LookupResult("fresh", entry, entry.selected_model_id)


def upsert(data_dir: Path, entry: ResearchEntry, *, as_of: date | None = None) -> ResearchCache:
    today = as_of or date.today()
    if entry.verified_at > today or entry.expires_at < today:
        raise ValueError("review date must be current and entry unexpired")
    context = load_context(data_dir)
    issue = _registry_issue(entry, context)
    if issue:
        raise ValueError(issue)
    retained = [
        item for item in context.cache.entries
        if (item.task, item.subject_type) != (entry.task, entry.subject_type)
    ]
    updated = ResearchCache(entries=sorted(
        [*retained, entry], key=lambda item: (item.task, item.subject_type),
    ))
    destination = data_dir / "research_cache.json"
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(updated.model_dump_json(indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, destination)
    return updated
