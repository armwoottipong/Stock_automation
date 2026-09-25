"""Registry schema and conservative model eligibility filtering."""

import json
from datetime import date
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
    precision: list[str] = Field(default_factory=list)
    commercial_use: CommercialUse = "unclear"
    license: str = ""
    source: str = ""
    comfyui: bool = False
    python: bool = False
    installed: bool = False
    local_path: str | None = None
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
    verified_at: date
    expires_at: date


class ResearchCache(BaseModel):
    schema_version: Literal[1] = 1
    entries: list[ResearchEntry] = Field(default_factory=list)
