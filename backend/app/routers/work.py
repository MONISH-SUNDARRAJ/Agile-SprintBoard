
"""User stories (by id) and tasks."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from .deps import get_or_404, check_assignee, story_out

router = APIRouter(prefix="/api", tags=["stories & tasks"])


def _story(db: Session, story_id: int) -> models.UserStory:
    """Load a story and its tasks, returning 404 when missing."""
    get_or_404(db, models.UserStory, story_id, "Story")

    return (
        db.query(models.UserStory)
        .options(selectinload(models.UserStory.tasks))
        .filter(models.UserStory.id == story_id)
        .one()
    )


def _sync_story_status(db: Session, story_id: int) -> None:
    """Synchronize the parent story status with its tasks."""
    story = db.get(models.UserStory, story_id)

    if story is None:
        return

    statuses = [
        status
        for (status,) in (
            db.query(models.Task.status)
            .filter(models.Task.story_id == story_id)
            .all()
        )
    ]

    # Preserve the existing status when there are no tasks.
    if not statuses:
        return

    if all(status == "done" for status in statuses):
        story.status = "done"
    elif all(status == "todo" for status in statuses):
        story.status = "todo"
    else:
        story.status = "in_progress"


@router.get(
    "/stories/{story_id}",
    response_model=schemas.StoryOut,
)
def get_story(
    story_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    return story_out(_story(db, story_id))


@router.patch(
    "/stories/{story_id}",
    response_model=schemas.StoryOut,
)
def update_story(
    story_id: int,
    data: schemas.StoryUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    story = _story(db, story_id)
    changes = data.model_dump(exclude_unset=True)

    if "assignee_id" in changes:
        check_assignee(db, changes["assignee_id"])

    for key, value in changes.items():
        if value is not None or key in ("assignee_id", "story_points"):
            setattr(story, key, value)

    db.commit()

    return story_out(_story(db, story_id))


@router.delete("/stories/{story_id}", status_code=204)
def delete_story(
    story_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    story = get_or_404(db, models.UserStory, story_id, "Story")

    db.delete(story)
    db.commit()

    return Response(status_code=204)


@router.get(
    "/stories/{story_id}/tasks",
    response_model=list[schemas.TaskOut],
)
def list_tasks(
    story_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    get_or_404(db, models.UserStory, story_id, "Story")

    return (
        db.query(models.Task)
        .filter(models.Task.story_id == story_id)
        .order_by(models.Task.id)
        .all()
    )


@router.post(
    "/stories/{story_id}/tasks",
    response_model=schemas.TaskOut,
    status_code=201,
)
def create_task(
    story_id: int,
    data: schemas.TaskIn,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    get_or_404(db, models.UserStory, story_id, "Story")
    check_assignee(db, data.assignee_id)

    task = models.Task(
        story_id=story_id,
        **data.model_dump(),
    )

    db.add(task)
    db.flush()

    # Synchronize the story after creating a task.
    _sync_story_status(db, story_id)

    db.commit()
    db.refresh(task)

    return task


@router.patch(
    "/tasks/{task_id}",
    response_model=schemas.TaskOut,
)
def update_task(
    task_id: int,
    data: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    task = get_or_404(db, models.Task, task_id, "Task")
    story_id = task.story_id

    changes = data.model_dump(exclude_unset=True)

    if "assignee_id" in changes:
        check_assignee(db, changes["assignee_id"])

    for key, value in changes.items():
        if value is not None or key in ("assignee_id", "due_date"):
            setattr(task, key, value)

    # Update the parent story after changing task fields.
    _sync_story_status(db, story_id)

    db.commit()
    db.refresh(task)

    return task


@router.delete("/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    task = get_or_404(db, models.Task, task_id, "Task")
    story_id = task.story_id

    db.delete(task)
    db.flush()

    # Recalculate the parent story after deleting a task.
    _sync_story_status(db, story_id)

    db.commit()

    return Response(status_code=204)
