"""Registry schema and conservative model eligibility filtering."""

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator


CommercialUse = Literal["allowed", "restricted", "unclear"]


class ModelRecord(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    version: str = ""
    category: list[str] = Field(default_factory=list)
    tasks: list[str] = Field(default_factory=list)
    vram_gb: float | None = Field(default=None, gt=0)
    native_scale: Literal[2, 4] | None = None
    precision: list[str] = Field(default_factory=list)
    commercial_use: CommercialUse = "unclear"
    license: str = ""
    source: str = ""
    comfyui: bool = False
    python: bool = False
    installed: bool = False
    local_path: str | None = None
    sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    known_issues: list[str] = Field(default_factory=list)
    last_verified: date | None = None


class Registry(BaseModel):
    schema_version: Literal[1] = 1
    records: list[ModelRecord] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_ids(self) -> "Registry":
        ids = [record.id for record in self.records]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate registry id")
        return self

    def eligible(self, task: str, *, commercial: bool = False) -> list[ModelRecord]:
        return [
            record for record in self.records
            if task in record.tasks
            and (
                not commercial
                or (
                    record.commercial_use == "allowed"
                    and bool(record.license)
                    and bool(record.source)
                    and record.last_verified is not None
                )
            )
        ]


def load_registry(path: Path) -> Registry:
    with path.open(encoding="utf-8") as stream:
        return Registry.model_validate(json.load(stream))


class LicenseRecord(BaseModel):
    resource_id: str = Field(min_length=1)
    license: str = Field(min_length=1)
    commercial_use: CommercialUse = "unclear"
    source: str = Field(min_length=1)
    last_verified: date


class LicenseRegistry(BaseModel):
    schema_version: Literal[1] = 1
    records: list[LicenseRecord] = Field(default_factory=list)


class ToolRecord(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    version: str = ""
    source: str = ""
    license: str = ""
    commercial_use: CommercialUse = "unclear"
    installed: bool = False
    local_path: str | None = None
    last_verified: date | None = None


class ToolRegistry(BaseModel):
    schema_version: Literal[1] = 1
    records: list[ToolRecord] = Field(default_factory=list)


class ResearchEntry(BaseModel):
    task: str = Field(min_length=1)
    subject_type: str = Field(min_length=1)
    candidate_ids: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    outcome: Literal["selected", "manual_review", "no_selection"] = "no_selection"
    selected_model_id: str | None = None
    benchmark_path: str | None = None
    summary: str = ""
    verified_at: date
    expires_at: date

    @model_validator(mode="after")
    def valid_decision(self) -> "ResearchEntry":
        if not self.candidate_ids or len(set(self.candidate_ids)) != len(self.candidate_ids):
            raise ValueError("research entry requires unique candidate_ids")
        if not self.sources or any(not source.startswith("https://") for source in self.sources):
            raise ValueError("research entry requires HTTPS source URLs")
        if self.outcome == "selected":
            if self.selected_model_id not in self.candidate_ids:
                raise ValueError("selected_model_id must be one of candidate_ids")
            if not self.benchmark_path:
                raise ValueError("selected research entry requires benchmark_path")
        elif self.selected_model_id is not None:
            raise ValueError("non-selected outcome cannot have selected_model_id")
        if self.expires_at < self.verified_at or self.expires_at > self.verified_at + timedelta(days=30):
            raise ValueError("research entry expires_at must be within 30 days of verified_at")
        return self


class ResearchCache(BaseModel):
    schema_version: Literal[1] = 1
    entries: list[ResearchEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_keys(self) -> "ResearchCache":
        keys = [(entry.task, entry.subject_type) for entry in self.entries]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate research cache key")
        return self
