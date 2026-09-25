from typing import List

from pydantic import BaseModel, Field


class CitationFinding(BaseModel):
    id: int
    section: str | None = None

    claim_text: str

    claim_type: str | None = None

    citation_present: str
    citation_needed: str

    citation_status: str | None = None

    confidence: float | None = None

    suggested_source_id: int | None = None
    suggestion_reason: str | None = None


class CitationAnalysisResponse(BaseModel):
    report_id: int

    citation_coverage: float | None = None

    total_claims: int = 0
    citations_present: int = 0

    citation_required_claims: int = 0
    cited_required_claims: int = 0

    potential_missing_citations: int = 0

    own_research_claims: int = 0
    inherited_context_claims: int = 0
    ignored_artifacts: int = 0

    risk_level: str | None = None

    findings: List[CitationFinding] = Field(
        default_factory=list
    )
