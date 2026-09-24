from pydantic import BaseModel
from typing import List


class PublicationRequest(BaseModel):
    manuscript: str = ""
    research_field: str = ""


class PublicationResponse(BaseModel):
    project_id: int
    paper_id: int

    publication_strategy: str

    journal_recommendations: List[dict]
    conference_recommendations: List[dict]

    publication_fit: dict

    predatory_risk_checks: List[dict]

    submission_checklist: List[dict]
    manuscript_requirements: List[str]
    missing_submission_items: List[str]

    cfp_and_deadline_notes: List[str]

    preparation_plan: List[dict]

    important_warnings: List[str]