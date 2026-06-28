import logging

from sqlalchemy.orm import Session

from models.notification import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    def create_notification(
        self,
        db: Session,
        user_id: int,
        title: str,
        message: str,
        type: str,
        priority: str = "Low",
    ):
        logger.info(
            f"Creating {priority} priority notification for user {user_id}: {title}"
        )
        notif = Notification(
            user_id=user_id, title=title, message=message, type=type, priority=priority
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)

        # In an enterprise app, we'd also emit a WebSocket event here to update the frontend instantly
        return notif

    def get_unread_notifications(self, db: Session, user_id: int):
        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read.is_(False))
            .order_by(Notification.created_at.desc())
            .all()
        )

    def mark_as_read(self, db: Session, notification_id: int):
        notif = (
            db.query(Notification).filter(Notification.id == notification_id).first()
        )
        if notif:
            notif.is_read = True
            db.commit()
            return True
        return False


notification_service = NotificationService()
