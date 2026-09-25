from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ManuscriptCreate(BaseModel):
    paper_id: int | None = None

    title: str = ""

    abstract: str = ""

    keywords: list[str] = Field(
        default_factory=list
    )

    sections: dict[str, str] = Field(
        default_factory=dict
    )


class ManuscriptUpdate(BaseModel):
    paper_id: int | None = None

    title: str = ""

    abstract: str = ""

    keywords: list[str] = Field(
        default_factory=list
    )

    sections: dict[str, str] = Field(
        default_factory=dict
    )

    status: str = "draft"

    change_summary: str = ""


class ManuscriptResponse(BaseModel):
    id: int
    project_id: int
    paper_id: int | None

    title: str
    abstract: str

    keywords: list[str]
    sections: dict[str, str]

    status: str
    current_version: int

    word_count: int
    character_count: int

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ManuscriptVersionResponse(BaseModel):
    id: int
    manuscript_id: int

    version_number: int

    title: str
    abstract: str

    keywords: list[str]
    sections: dict[str, str]

    change_summary: str | None

    created_at: datetime

    class Config:
        from_attributes = True


class WritingAssistRequest(BaseModel):
    instruction: str = Field(
        min_length=1,
        max_length=5000,
    )

    section_name: str = ""

    content: str = ""

    mode: str = "improve"


class WritingAssistResponse(BaseModel):
    success: bool
    section_name: str

    original_text: str
    improved_text: str

    evidence_note: str


class WritingReadinessResponse(BaseModel):
    project_id: int
    manuscript_id: int

    readiness_percentage: int

    completed_checks: int
    total_checks: int

    missing_sections: list[str]

    missing_citations: list[str]

    unsupported_claims: list[str]

    incomplete_methodology: list[str]

    missing_results: list[str]

    missing_references: bool

    word_count: int