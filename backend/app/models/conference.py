from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float
from sqlalchemy.sql import func
from app.database.database import Base

class Conference(Base):
    __tablename__ = "conferences"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(500), nullable=False)
    category = Column(String(120), nullable=False, index=True)
    location = Column(String(255), nullable=True)
    mode = Column(String(50), nullable=True)
    scope = Column(Text, nullable=True)
    cfp_opening = Column(DateTime(timezone=True), nullable=True)
    abstract_deadline = Column(DateTime(timezone=True), nullable=True)
    paper_deadline = Column(DateTime(timezone=True), nullable=True)
    notification_date = Column(DateTime(timezone=True), nullable=True)
    camera_ready_deadline = Column(DateTime(timezone=True), nullable=True)
    conference_date = Column(DateTime(timezone=True), nullable=True)
    source_url = Column(Text, nullable=True)
    source_name = Column(String(255), nullable=True)
    verification_status = Column(String(60), default="unverified", nullable=False)
    last_checked_at = Column(DateTime(timezone=True), server_default=func.now())
    active = Column(Boolean, default=True, nullable=False)

class ConferenceSource(Base):
    __tablename__ = "conference_sources"
    id = Column(Integer, primary_key=True, index=True)
    conference_id = Column(Integer, nullable=False, index=True)
    url = Column(Text, nullable=False)
    source_name = Column(String(255), nullable=True)
    checked_at = Column(DateTime(timezone=True), server_default=func.now())
    verification_status = Column(String(60), default="unverified", nullable=False)
