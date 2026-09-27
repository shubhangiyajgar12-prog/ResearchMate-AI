from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.sql import func
from app.database.database import Base


class ResearchTopic(Base):
    __tablename__ = "research_topics"
    __table_args__ = (
        UniqueConstraint("project_id", "topic", name="uq_research_topic_project_topic"),
    )

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("research_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    topic = Column(String(500), nullable=False)
    source_query = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
