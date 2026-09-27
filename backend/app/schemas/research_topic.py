from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ResearchTopicCreate(BaseModel):
    topic: str = Field(min_length=2, max_length=500)
    source_query: str | None = Field(default=None, max_length=500)
    description: str | None = None


class ResearchTopicResponse(BaseModel):
    id: int
    project_id: int
    topic: str
    source_query: str | None = None
    description: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
