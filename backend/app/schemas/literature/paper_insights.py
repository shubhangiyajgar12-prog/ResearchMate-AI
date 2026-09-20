from pydantic import BaseModel, Field
from typing import List


class PaperInsightsRequest(BaseModel):
    filename: str
    title: str | None = None
    abstract: str | None = None

    methodology: str | None = None
    dataset: str | None = None
    results: str | None = None

    key_findings: List[str] = Field(default_factory=list)
    limitations: str | None = None
    future_work: str | None = None


class PaperInsightsResponse(BaseModel):
    research_problem: str | None = None
    research_objective: str | None = None
    methodology_summary: str | None = None

    key_contributions: List[str] = Field(default_factory=list)

    research_gap: List[str] = Field(default_factory=list)

    limitations: List[str] = Field(default_factory=list)

    novelty_indicators: List[str] = Field(default_factory=list)

    possible_improvements: List[str] = Field(default_factory=list)

    future_research_directions: List[str] = Field(default_factory=list)

    evidence_note: str = (
        "Insights are generated from the information extracted from the paper. "
        "Researchers should verify these interpretations against the original paper."
    )