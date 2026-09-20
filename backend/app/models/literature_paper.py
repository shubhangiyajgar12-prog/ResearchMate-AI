from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func

from app.database.database import Base


class LiteraturePaper(Base):
    __tablename__ = "literature_papers"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey(
            "research_projects.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    paper_id = Column(String(255), nullable=True)

    title = Column(
        String(1000),
        nullable=False
    )

    abstract = Column(
        Text,
        nullable=True
    )

    year = Column(
        Integer,
        nullable=True
    )

    authors = Column(
        Text,
        nullable=True
    )

    citation_count = Column(
        Integer,
        nullable=True
    )

    url = Column(
        Text,
        nullable=True
    )

    doi = Column(
        String(500),
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )