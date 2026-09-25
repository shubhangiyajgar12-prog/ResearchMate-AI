from pydantic import BaseModel
from typing import List, Optional


class WritingAnalysisRequest(BaseModel):
    title: Optional[str] = ""
    abstract: Optional[str] = ""
    manuscript: Optional[str] = ""


class TitleSuggestion(BaseModel):
    title: str
    reason: str


class WritingAnalysisResponse(BaseModel):
    project_id: int
    paper_id: int

    paper_structure: dict

    title_suggestions: List[TitleSuggestion]

    abstract_feedback: dict

    academic_writing_feedback: dict

    citation_reference_feedback: dict

    formatting_feedback: dict

    overall_recommendations: List[str]

    strengths: List[str]

    improvement_areas: List[str]
