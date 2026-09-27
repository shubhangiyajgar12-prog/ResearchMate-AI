
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from app.database.database import Base


class Manuscript(Base):
    __tablename__ = "manuscripts"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    project_id = Column(
        Integer,
        ForeignKey(
            "research_projects.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    paper_id = Column(
        Integer,
        ForeignKey(
            "literature_papers.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    title = Column(
        String(1000),
        nullable=True,
    )

    abstract = Column(
        Text,
        nullable=True,
    )

    keywords = Column(
        JSON,
        nullable=False,
        default=list,
    )

    sections = Column(
        JSON,
        nullable=False,
        default=dict,
    )

    status = Column(
        String(50),
        nullable=False,
        default="draft",
    )

    current_version = Column(
        Integer,
        nullable=False,
        default=1,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ManuscriptVersion(Base):
    __tablename__ = "manuscript_versions"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    manuscript_id = Column(
        Integer,
        ForeignKey(
            "manuscripts.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    version_number = Column(
        Integer,
        nullable=False,
    )

    title = Column(
        String(1000),
        nullable=True,
    )

    abstract = Column(
        Text,
        nullable=True,
    )

    keywords = Column(
        JSON,
        nullable=False,
        default=list,
    )

    sections = Column(
        JSON,
        nullable=False,
        default=dict,
    )

    change_summary = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

class ManuscriptSection(Base):
    """
    Normalized persistence for individual manuscript sections.

    The legacy JSON ``Manuscript.sections`` field remains for backward
    compatibility with the existing frontend/API. This table is the
    authoritative section-level store for status, counts, provenance,
    and generation metadata.
    """

    __tablename__ = "manuscript_sections"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("research_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    manuscript_id = Column(
        Integer,
        ForeignKey("manuscripts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    section_key = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=False, default="")
    content = Column(Text, nullable=False, default="")
    status = Column(
        String(30),
        nullable=False,
        default="not_started",
    )
    version = Column(Integer, nullable=False, default=1)
    word_count = Column(Integer, nullable=False, default=0)
    character_count = Column(Integer, nullable=False, default=0)
    generated_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    source_paper_ids = Column(
        JSON,
        nullable=False,
        default=list,
    )
    generation_metadata = Column(
        JSON,
        nullable=False,
        default=dict,
    )

    __table_args__ = (
        UniqueConstraint(
            "manuscript_id",
            "section_key",
            name="uq_manuscript_section_key",
        ),
    )
