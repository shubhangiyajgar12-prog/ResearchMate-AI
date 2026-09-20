from pydantic import BaseModel, Field
from typing import List


class ResearchQuestionRequest(BaseModel):

    topic: str = Field(
        ...,
        min_length=5,
        max_length=500
    )

    research_gaps: List[str] = Field(
        default_factory=list
    )


class ResearchQuestionResponse(BaseModel):

    topic: str

    research_area: str

    research_questions: List[str]

    hypothesis: str

    variables: List[str]

    research_direction: str