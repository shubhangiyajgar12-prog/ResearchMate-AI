from pydantic import BaseModel, Field
from typing import List


class LiteraturePaperCreate(BaseModel):
    project_id: int
    paper_id: str | None = None
    title: str
    abstract: str | None = None
    year: int | None = None
    authors: List[str] = Field(default_factory=list)
    citation_count: int | None = None
    url: str | None = None
    doi: str | None = None


class LiteraturePaperResponse(LiteraturePaperCreate):
    id: int

    class Config:
        from_attributes = True


class LiteratureMatrixRequest(BaseModel):
    project_id: int
    paper_ids: List[int] = Field(
        ...,
        min_length=1,
        max_length=20
    )


class LiteratureMatrixRow(BaseModel):
    paper_id: int
    title: str
    year: int | None = None
    authors: List[str] = Field(default_factory=list)

    research_problem: str | None = None
    methodology: str | None = None
    dataset: str | None = None
    key_results: str | None = None
    limitations: str | None = None
    research_gap: str | None = None


class LiteratureMatrixResponse(BaseModel):
    project_id: int

    papers: List[LiteratureMatrixRow] = Field(
        default_factory=list
    )

    cross_paper_findings: List[str] = Field(
        default_factory=list
    )

    common_methods: List[str] = Field(
        default_factory=list
    )

    common_limitations: List[str] = Field(
        default_factory=list
    )

    potential_research_gaps: List[str] = Field(
        default_factory=list
    )

    evidence_note: str = (
        "Matrix insights are generated from the selected "
        "paper information. Verify important claims against "
        "the original papers."
    )