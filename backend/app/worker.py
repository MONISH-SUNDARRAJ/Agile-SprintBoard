"""Background workflow: overdue-task reminders.

Flow (per scheduled run, every OVERDUE_CHECK_MINUTES, or on demand via the API):
  1. Find tasks that are past due, not done, and assigned to someone.
  2. Skip tasks that already got a reminder today (idempotent: safe to run twice).
  3. For each task create a JobLog row and try to deliver the reminder.
  4. On failure, retry with exponential backoff, up to JOB_MAX_ATTEMPTS.
  5. If every attempt fails, mark the JobLog 'failed' with the error. The next
     scheduled run picks the task up again, because no reminder exists yet today.

One task failing never blocks the others.
"""
import logging
import random
import time
from datetime import date, datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from . import config, models
from .database import SessionLocal

log = logging.getLogger("sprintboard.worker")
JOB_TYPE = "overdue_reminder"


class DeliveryError(Exception):
    pass


def deliver_reminder(db: Session, task: models.Task) -> None:
    """Deliver one reminder. Today this writes an in-app notification.
    Swap in email/Slack here; raise DeliveryError on failure and the retry logic handles it."""
    if random.random() < config.DELIVERY_FAIL_RATE:  # demo switch to exercise retries
        raise DeliveryError("Simulated delivery failure")
    db.add(models.Notification(
        user_id=task.assignee_id, task_id=task.id, kind="overdue",
        message=f'"{task.title}" was due on {task.due_date.isoformat()} and is not done yet.',
    ))


def _already_reminded_today(db: Session, task_id: int) -> bool:
    today = datetime.now(timezone.utc).date()  # created_at is stored in UTC
    return db.query(models.Notification.id).filter(
        models.Notification.task_id == task_id,
        models.Notification.kind == "overdue",
        func.date(models.Notification.created_at) == today.isoformat(),
    ).first() is not None


def _process_task(db: Session, task: models.Task) -> None:
    job = models.JobLog(job_type=JOB_TYPE, task_id=task.id, status="pending")
    db.add(job)
    db.commit()
    for attempt in range(1, config.JOB_MAX_ATTEMPTS + 1):
        job.attempts = attempt
        try:
            deliver_reminder(db, task)
            job.status, job.error_message = "success", None
            job.finished_at = datetime.now(timezone.utc)
            db.commit()  # notification and job status commit together
            return
        except Exception as exc:  # noqa: BLE001 - any delivery error is retryable
            db.rollback()
            job.attempts, job.error_message = attempt, str(exc)[:500]
            db.add(job)
            db.commit()
            log.warning("Reminder for task %s failed (attempt %s/%s): %s",
                        task.id, attempt, config.JOB_MAX_ATTEMPTS, exc)
            if attempt < config.JOB_MAX_ATTEMPTS:
                time.sleep(config.JOB_BACKOFF_SECONDS * 2 ** (attempt - 1))
    job.status, job.finished_at = "failed", datetime.now(timezone.utc)
    db.commit()
    log.error("Reminder for task %s gave up after %s attempts", task.id, config.JOB_MAX_ATTEMPTS)


def run_overdue_check() -> dict:
    """Entry point for the scheduler and the manual-trigger endpoint."""
    db = SessionLocal()
    stats = {"checked": 0, "sent": 0, "failed": 0}
    try:
        overdue = (db.query(models.Task)
                   .filter(models.Task.due_date < date.today(),
                           models.Task.status != "done",
                           models.Task.assignee_id.isnot(None)).all())
        for task in overdue:
            if _already_reminded_today(db, task.id):
                continue
            stats["checked"] += 1
            _process_task(db, task)
            db.refresh(task)
            job = (db.query(models.JobLog).filter(models.JobLog.task_id == task.id)
                   .order_by(models.JobLog.id.desc()).first())
            stats["sent" if job and job.status == "success" else "failed"] += 1
    except Exception:  # noqa: BLE001 - the scheduler must survive any run
        log.exception("Overdue check crashed")
    finally:
        db.close()
    log.info("Overdue check finished: %s", stats)
    return stats
