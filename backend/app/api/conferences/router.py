from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.conference import Conference
from app.models.notification import Notification

router = APIRouter(prefix="/conferences", tags=["Conference Intelligence"])

@router.get("")
def list_conferences(category: str | None = Query(None), query: str | None = Query(None), db: Session = Depends(get_db)):
    q = db.query(Conference).filter(Conference.active == True)
    if category and category.lower() != "all": q = q.filter(Conference.category.ilike(f"%{category}%"))
    if query: q = q.filter((Conference.name.ilike(f"%{query}%")) | (Conference.scope.ilike(f"%{query}%")))
    items = q.order_by(Conference.paper_deadline.asc().nullslast(), Conference.id.desc()).limit(100).all()
    return [{"id": x.id, "name": x.name, "category": x.category, "location": x.location, "mode": x.mode, "scope": x.scope, "paper_deadline": x.paper_deadline, "conference_date": x.conference_date, "source_url": x.source_url, "source_name": x.source_name, "verification_status": x.verification_status, "last_checked_at": x.last_checked_at} for x in items]

@router.post("")
def create_conference(payload: dict, db: Session = Depends(get_db)):
    item = Conference(**{k: payload.get(k) for k in ["name","category","location","mode","scope","cfp_opening","abstract_deadline","paper_deadline","notification_date","camera_ready_deadline","conference_date","source_url","source_name","verification_status"] if payload.get(k) is not None})
    db.add(item); db.commit(); db.refresh(item)
    db.add(Notification(type="conference_new", title="New conference opportunity found", message=f"{item.name} was added to Conference Intelligence.", entity_id=item.id, entity_type="conference", source_url=item.source_url))
    db.commit()
    return {"id": item.id, "message": "Conference added", "verification_status": item.verification_status}

@router.get("/categories")
def categories():
    return ["AI / Machine Learning","Computer Vision","NLP","Data Science","Cybersecurity","IoT","Cloud Computing","Software Engineering","Blockchain","Robotics","Information Technology","General Computer Science"]
