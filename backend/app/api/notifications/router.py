from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.database import get_db
from app.models.notification import Notification

router = APIRouter(prefix="/notifications", tags=["Notifications"])

@router.get("")
def notifications(db: Session = Depends(get_db)):
    rows = db.query(Notification).filter(Notification.is_dismissed == False).order_by(Notification.created_at.desc()).limit(50).all()
    return [{"id": n.id, "type": n.type, "title": n.title, "message": n.message, "entity_id": n.entity_id, "entity_type": n.entity_type, "source_url": n.source_url, "is_read": n.is_read, "created_at": n.created_at} for n in rows]

@router.patch("/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if not n: raise HTTPException(404, "Notification not found")
    n.is_read = True; db.commit(); return {"success": True}

@router.patch("/read-all")
def mark_all_read(db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.is_read == False, Notification.is_dismissed == False).update({Notification.is_read: True}, synchronize_session=False)
    db.commit(); return {"success": True}

@router.patch("/{notification_id}/dismiss")
def dismiss(notification_id: int, db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if not n: raise HTTPException(404, "Notification not found")
    n.is_dismissed = True; db.commit(); return {"success": True}
