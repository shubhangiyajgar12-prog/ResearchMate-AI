from pydantic import BaseModel
from typing import List


class ReviewerRequest(BaseModel):
    manuscript: str = ""


class ReviewerResponse(BaseModel):
    project_id: int
    paper_id: int

    overall_review: str

    novelty_review: dict
    methodology_review: dict
    dataset_review: dict
    experiment_review: dict
    results_review: dict
    discussion_review: dict
    citation_review: dict

    major_concerns: List[str]
    minor_concerns: List[str]

    technical_issues: List[str]
    reviewer_questions: List[str]

    strengths: List[str]
    improvement_priorities: List[str]

    reviewer_recommendation: str