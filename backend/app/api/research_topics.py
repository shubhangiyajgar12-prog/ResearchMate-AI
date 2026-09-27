from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.research_project import ResearchProject
from app.models.research_topic import ResearchTopic
from app.schemas.research_topic import ResearchTopicCreate, ResearchTopicResponse

router = APIRouter(prefix="/projects/{project_id}/topics", tags=["Research Topics"])


def _project(db: Session, project_id: int):
    project = db.query(ResearchProject).filter(ResearchProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Research project not found.")
    return project


@router.get("", response_model=list[ResearchTopicResponse])
def list_topics(project_id: int, db: Session = Depends(get_db)):
    _project(db, project_id)
    return (
        db.query(ResearchTopic)
        .filter(ResearchTopic.project_id == project_id)
        .order_by(ResearchTopic.created_at.desc(), ResearchTopic.id.desc())
        .all()
    )


@router.post("", response_model=ResearchTopicResponse, status_code=201)
def add_topic(project_id: int, payload: ResearchTopicCreate, db: Session = Depends(get_db)):
    _project(db, project_id)
    topic = payload.topic.strip()
    if len(topic) < 2:
        raise HTTPException(status_code=422, detail="Topic must contain at least 2 characters.")

    existing = (
        db.query(ResearchTopic)
        .filter(ResearchTopic.project_id == project_id, ResearchTopic.topic.ilike(topic))
        .first()
    )
    if existing:
        return existing

    row = ResearchTopic(
        project_id=project_id,
        topic=topic,
        source_query=(payload.source_query or topic).strip() or topic,
        description=(payload.description or "").strip() or None,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{topic_id}")
def delete_topic(project_id: int, topic_id: int, db: Session = Depends(get_db)):
    _project(db, project_id)
    row = (
        db.query(ResearchTopic)
        .filter(ResearchTopic.id == topic_id, ResearchTopic.project_id == project_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Research topic not found in this project.")
    db.delete(row)
    db.commit()
    return {"success": True, "deleted_topic_id": topic_id}
