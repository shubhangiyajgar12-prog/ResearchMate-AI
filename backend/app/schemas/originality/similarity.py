from typing import List

from pydantic import BaseModel, Field


class SimilarityMatchResponse(BaseModel):
    id: int

    source_paper_id: int | None = None
    source_title: str | None = None
    source_url: str | None = None
    source_doi: str | None = None

    matched_text: str
    source_text: str | None = None

    similarity_score: float
    match_type: str
    section: str | None = None


class OriginalityAnalysisRequest(BaseModel):
    project_id: int
    paper_id: int


class OriginalityReportResponse(BaseModel):
    id: int
    project_id: int
    paper_id: int

    overall_similarity: float | None = None
    exact_similarity: float | None = None
    semantic_similarity: float | None = None

    semantic_similarity_available: bool = False

    lexical_similarity: float | None = None

    target_chunks: int = 0
    sources_checked: int = 0
    duplicate_sources_excluded_count: int = 0

    total_matches: int = 0
    potential_missing_citations: int = 0

    risk_level: str | None = None

    limitations: List[str] = Field(
        default_factory=list
    )

    matches: List[SimilarityMatchResponse] = Field(
        default_factory=list
    )
