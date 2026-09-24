from sqlalchemy import Column, Integer, Float, Text, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database.database import Base


class CitationAnalysis(Base):
    __tablename__ = "citation_analysis"

    id = Column(Integer, primary_key=True, index=True)

    report_id = Column(
        Integer,
        ForeignKey("originality_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    section = Column(String(255), nullable=True)

    claim_text = Column(Text, nullable=False)

    citation_present = Column(
        String(20),
        nullable=False,
    )

    citation_needed = Column(
        String(20),
        nullable=False,
    )

    confidence = Column(Float, nullable=True)

    suggested_source_id = Column(
        Integer,
        ForeignKey("literature_papers.id", ondelete="SET NULL"),
        nullable=True,
    )

    suggestion_reason = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )