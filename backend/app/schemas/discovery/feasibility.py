from pydantic import BaseModel, Field


class FeasibilityAnalysisRequest(BaseModel):

    topic: str = Field(
        ...,
        min_length=5,
        max_length=500
    )


class FeasibilityAnalysisResponse(BaseModel):

    topic: str

    research_area: str

    dataset_feasibility: str

    computational_feasibility: str

    implementation_complexity: str

    evaluation_feasibility: str

    overall_feasibility: str

    feasibility_score: float

    challenges: list[str]

    recommendations: list[str]