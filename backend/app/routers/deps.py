"""Shared helpers: lookups that 404 cleanly, and progress calculation."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas


def get_or_404(db: Session, model, obj_id: int, label: str):
    obj = db.get(model, obj_id)
    if not obj:
        raise HTTPException(404, f"{label} not found")
    return obj


def check_assignee(db: Session, assignee_id: int | None):
    if assignee_id is not None and not db.get(models.User, assignee_id):
        raise HTTPException(422, "assignee_id does not match any user")


def story_out(story: models.UserStory) -> schemas.StoryOut:
    total = len(story.tasks)
    done = sum(1 for t in story.tasks if t.status == "done")
    out = schemas.StoryOut.model_validate(story)
    out.total_tasks, out.done_tasks = total, done
    out.progress = round(done / total, 3) if total else 0.0
    return out


def project_out(project: models.Project) -> schemas.ProjectOut:
    tasks = [t for s in project.stories for t in s.tasks]
    done = sum(1 for t in tasks if t.status == "done")
    out = schemas.ProjectOut.model_validate(project)
    out.story_count = len(project.stories)
    out.total_tasks, out.done_tasks = len(tasks), done
    out.progress = round(done / len(tasks), 3) if tasks else 0.0
    return out
