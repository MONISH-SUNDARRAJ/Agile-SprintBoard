from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import models, schemas, worker
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/api", tags=["notifications & jobs"])


@router.get("/notifications", response_model=list[schemas.NotificationOut])
def my_notifications(unread_only: bool = False, db: Session = Depends(get_db),
                     user: models.User = Depends(get_current_user)):
    q = db.query(models.Notification).filter(models.Notification.user_id == user.id)
    if unread_only:
        q = q.filter(models.Notification.is_read.is_(False))
    return q.order_by(models.Notification.created_at.desc()).limit(100).all()


@router.post("/notifications/{notification_id}/read", response_model=schemas.NotificationOut)
def mark_read(notification_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    n = db.get(models.Notification, notification_id)
    if not n or n.user_id != user.id:  # same error for missing and foreign: don't leak existence
        raise HTTPException(404, "Notification not found")
    n.is_read = True
    db.commit()
    return n


@router.post("/jobs/overdue-check", status_code=202)
def trigger_overdue_check(background: BackgroundTasks, _: models.User = Depends(get_current_user)):
    """Run the overdue check now. Returns 202 immediately; the work happens in the background."""
    background.add_task(worker.run_overdue_check)
    return {"detail": "Overdue check started"}


@router.get("/jobs/logs", response_model=list[schemas.JobLogOut])
def job_logs(limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db),
             _: models.User = Depends(get_current_user)):
    return db.query(models.JobLog).order_by(models.JobLog.id.desc()).limit(limit).all()
