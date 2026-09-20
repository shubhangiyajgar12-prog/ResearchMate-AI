from pydantic import BaseModel, Field
from typing import List


class ResearchGapRequest(BaseModel):

    topic: str = Field(
        ...,
        min_length=5,
        max_length=500
    )


class ResearchGapResponse(BaseModel):

    topic: str

    research_area: str

    identified_gaps: List[str]

    gap_summary: str

    research_direction: str