from sqlalchemy import Column, Integer, Float, Text, String, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database.database import Base


class SimilarityMatch(Base):
    __tablename__ = "similarity_matches"

    id = Column(Integer, primary_key=True, index=True)

    report_id = Column(
        Integer,
        ForeignKey("originality_reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    source_paper_id = Column(
        Integer,
        ForeignKey("literature_papers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    source_title = Column(String(1000), nullable=True)
    source_url = Column(Text, nullable=True)
    source_doi = Column(String(500), nullable=True)

    matched_text = Column(Text, nullable=False)
    source_text = Column(Text, nullable=True)

    similarity_score = Column(Float, nullable=False)

    match_type = Column(
        String(50),
        nullable=False,
    )

    section = Column(String(255), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )