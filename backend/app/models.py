from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class DocumentRecord(BaseModel):
    id: str
    filename: str
    sha256: str
    size_bytes: int
    page_count: int | None = None
    extraction_status: Literal["pending", "extracted", "needs_ocr", "failed"]
    extracted_characters: int = 0
    error: str | None = None
    scanned_at: datetime


class ScanJob(BaseModel):
    id: str
    status: Literal["queued", "running", "completed", "failed"]
    total_files: int = 0
    processed_files: int = 0
    created_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


class ProgramField(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=1, max_length=120)
    description: str = ""
    required: bool = False
    value_type: Literal["text", "date", "number", "list", "select"] = "text"
    options: list[str] = Field(default_factory=list)


class ProgramSetup(BaseModel):
    version: int = Field(ge=0)
    definition: str = ""
    inclusion_rules: list[str] = Field(default_factory=list)
    exclusion_rules: list[str] = Field(default_factory=list)
    taxonomy: list[str] = Field(default_factory=list)
    fields: list[ProgramField] = Field(default_factory=list)
    evidence_rules: list[str] = Field(default_factory=list)


class ProgramSetupInput(BaseModel):
    definition: str = ""
    inclusion_rules: list[str] = Field(default_factory=list)
    exclusion_rules: list[str] = Field(default_factory=list)
    taxonomy: list[str] = Field(default_factory=list)
    fields: list[ProgramField] = Field(default_factory=list)
    evidence_rules: list[str] = Field(default_factory=list)


class EvidenceReference(BaseModel):
    document_id: str
    page_number: int = Field(ge=1)
    quote_nl: str = Field(min_length=1, max_length=4000)
    extracted_location: str | None = Field(default=None, max_length=250)
    reviewer_confirmed: bool = False


class ProgramRecord(BaseModel):
    id: str
    setup_version: int
    name_en: str = Field(min_length=1, max_length=250)
    classification: str | None = Field(default=None, max_length=160)
    field_values: dict[str, Any] = Field(default_factory=dict)
    status: Literal["draft", "reviewed"] = "draft"
    confidence: Literal["low", "medium", "high"] = "medium"
    evidence: list[EvidenceReference] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ProgramCreate(BaseModel):
    name_en: str = Field(min_length=1, max_length=250)
    classification: str | None = Field(default=None, max_length=160)
    field_values: dict[str, Any] = Field(default_factory=dict)
    status: Literal["draft", "reviewed"] = "draft"
    confidence: Literal["low", "medium", "high"] = "medium"


class ProgramUpdate(BaseModel):
    name_en: str | None = Field(default=None, min_length=1, max_length=250)
    classification: str | None = Field(default=None, max_length=160)
    field_values: dict[str, Any] | None = None
    status: Literal["draft", "reviewed"] | None = None
    confidence: Literal["low", "medium", "high"] | None = None


class AssistantRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class AssistantAnswer(BaseModel):
    provider: Literal["fake"]
    answer: str
    citations: list[EvidenceReference] = Field(default_factory=list)
