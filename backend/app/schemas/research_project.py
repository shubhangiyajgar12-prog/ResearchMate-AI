from pydantic import BaseModel
from datetime import datetime


class ResearchProjectCreate(BaseModel):
    title: str
    description: str | None = None
    research_field: str | None = None


class ResearchProjectUpdate(BaseModel):
    title: str
    description: str | None = None
    research_field: str | None = None
    status: str = "active"


class ResearchProjectResponse(BaseModel):
    id: int
    title: str
    description: str | None
    research_field: str | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True