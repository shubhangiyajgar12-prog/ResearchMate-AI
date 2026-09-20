from pydantic import BaseModel, Field
from typing import List


class TopicValidationRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=5,
        max_length=500
    )


class TopicValidationResponse(BaseModel):
    topic: str
    research_field: str
    specificity: str
    feasibility: str
    keywords: List[str]
    validation_summary: str