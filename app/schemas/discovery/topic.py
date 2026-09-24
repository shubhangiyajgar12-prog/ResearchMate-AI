from typing import List

from pydantic import BaseModel, Field


class TopicValidationRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Research topic to validate",
    )


class TopicValidationResponse(BaseModel):
    topic: str
    research_field: str
    specificity: str
    feasibility: str
    keywords: List[str]
    validation_summary: str