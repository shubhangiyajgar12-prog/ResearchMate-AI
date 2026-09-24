from pydantic import BaseModel
from typing import List


class CitationFinding(BaseModel):
    id: int
    section: str | None = None

    claim_text: str

    citation_present: str
    citation_needed: str

    confidence: float | None = None

    suggested_source_id: int | None = None
    suggestion_reason: str | None = None


class CitationAnalysisResponse(BaseModel):
    report_id: int

    citation_coverage: float | None = None
    total_claims: int = 0
    citations_present: int = 0
    potential_missing_citations: int = 0

    findings: List[CitationFinding] = []