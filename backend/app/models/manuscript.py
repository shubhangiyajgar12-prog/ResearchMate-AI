
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
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