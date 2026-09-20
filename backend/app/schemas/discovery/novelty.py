from pydantic import BaseModel, Field


class NoveltyAnalysisRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=5,
        max_length=500
    )


class NoveltyAnalysisResponse(BaseModel):
    topic: str
    research_area: str
    novelty_level: str
    novelty_score: float
    potential_gap: str
    recommendation: str