from pydantic import BaseModel, Field
from typing import List


# ============================================================
# REQUEST
# ============================================================

class ResearchGapRequest(BaseModel):
    paper_ids: List[int] = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Database IDs of selected literature papers"
    )


# ============================================================
# RESEARCH GAP ITEM
# ============================================================

class ResearchGapItem(BaseModel):
    gap: str

    evidence: List[str] = Field(
        default_factory=list
    )

    affected_papers: List[int] = Field(
        default_factory=list
    )

    evidence_strength: str = "moderate"

    research_opportunity: str


# ============================================================
# RESPONSE
# ============================================================

class ResearchGapResponse(BaseModel):
    project_id: int

    papers_analyzed: int

    research_gaps: List[ResearchGapItem] = Field(
        default_factory=list
    )

    cross_paper_patterns: List[str] = Field(
        default_factory=list
    )

    evidence_note: str = (
        "Research gaps are potential/open areas inferred "
        "from the selected papers. They should be verified "
        "against the original papers and broader literature."
    )