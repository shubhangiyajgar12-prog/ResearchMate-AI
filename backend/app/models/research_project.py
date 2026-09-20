from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func

from app.database.database import Base
from pydantic import BaseModel
from datetime import datetime

class ResearchProject(Base):
    __tablename__ = "research_projects"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)

    description = Column(Text, nullable=True)

    research_field = Column(String(100), nullable=True)

    status = Column(
        String(50),
        default="active",
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )
class ResearchProjectCreate(BaseModel):
    title: str
    description: str | None = None
    research_field: str | None = None


class ResearchProjectResponse(BaseModel):
    id: int
    title: str
    description: str | None
    research_field: str | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True