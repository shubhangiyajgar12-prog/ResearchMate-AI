from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from app.database.database import Base


class PaperAnalysis(Base):
    __tablename__ = "paper_analyses"

    id = Column(Integer, primary_key=True, index=True)
    literature_paper_id = Column(
        Integer,
        ForeignKey("literature_papers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    project_id = Column(Integer, nullable=False, index=True)
    filename = Column(String(500), nullable=True)
    analysis_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
