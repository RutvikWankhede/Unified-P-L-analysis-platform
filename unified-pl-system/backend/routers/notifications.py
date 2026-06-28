from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.security import get_current_user
from database import get_db
from models.user import User
from services.notification_service import notification_service

router = APIRouter()


@router.get("/")
def get_notifications(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    notifications = notification_service.get_unread_notifications(db, current_user.id)
    return {
        "unread_count": len(notifications),
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "priority": n.priority,
                "created_at": n.created_at,
            }
            for n in notifications
        ],
    }


@router.post("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    success = notification_service.mark_as_read(db, notification_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification marked as read"}
