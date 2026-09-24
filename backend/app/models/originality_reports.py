from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func

from app.database.database import Base


class OriginalityReport(Base):
    __tablename__ = "originality_reports"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    paper_id = Column(
        Integer,
        ForeignKey("literature_papers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    overall_similarity = Column(Float, nullable=True)
    exact_similarity = Column(Float, nullable=True)
    semantic_similarity = Column(Float, nullable=True)

    total_matches = Column(Integer, default=0, nullable=False)
    potential_missing_citations = Column(Integer, default=0, nullable=False)

    risk_level = Column(String(50), nullable=True)

    report_json = Column(JSON, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )