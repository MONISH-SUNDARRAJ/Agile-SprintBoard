from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session, selectinload

from .. import models, schemas
from ..auth import get_current_user
from ..database import get_db
from .deps import get_or_404, check_assignee, project_out, story_out

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _load(db: Session, project_id: int) -> models.Project:
    p = (db.query(models.Project)
         .options(selectinload(models.Project.stories).selectinload(models.UserStory.tasks))
         .filter(models.Project.id == project_id).first())
    if not p:
        raise HTTPException(404, "Project not found")
    return p


@router.get("", response_model=list[schemas.ProjectOut])
def list_projects(db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    projects = (db.query(models.Project)
                .options(selectinload(models.Project.stories).selectinload(models.UserStory.tasks))
                .order_by(models.Project.created_at.desc()).all())
    return [project_out(p) for p in projects]


@router.post("", response_model=schemas.ProjectOut, status_code=201)
def create_project(data: schemas.ProjectIn, db: Session = Depends(get_db),
                   user: models.User = Depends(get_current_user)):
    p = models.Project(name=data.name.strip(), description=data.description, owner_id=user.id)
    db.add(p)
    db.commit()
    return project_out(p)


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    return project_out(_load(db, project_id))


@router.patch("/{project_id}", response_model=schemas.ProjectOut)
def update_project(project_id: int, data: schemas.ProjectUpdate, db: Session = Depends(get_db),
                   _: models.User = Depends(get_current_user)):
    p = _load(db, project_id)
    for k, v in data.model_dump(exclude_unset=True).items():
        if v is not None:
            setattr(p, k, v)
    db.commit()
    return project_out(p)


@router.delete("/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    p = get_or_404(db, models.Project, project_id, "Project")
    if p.owner_id != user.id:
        raise HTTPException(403, "Only the project owner can delete it")
    db.delete(p)  # stories and tasks go with it (ON DELETE CASCADE)
    db.commit()
    return Response(status_code=204)


@router.get("/{project_id}/stories", response_model=list[schemas.StoryOut])
def list_stories(project_id: int, db: Session = Depends(get_db), _: models.User = Depends(get_current_user)):
    p = _load(db, project_id)
    return [story_out(s) for s in sorted(p.stories, key=lambda s: s.created_at)]


@router.post("/{project_id}/stories", response_model=schemas.StoryOut, status_code=201)
def create_story(project_id: int, data: schemas.StoryIn, db: Session = Depends(get_db),
                 _: models.User = Depends(get_current_user)):
    get_or_404(db, models.Project, project_id, "Project")
    check_assignee(db, data.assignee_id)
    s = models.UserStory(project_id=project_id, **data.model_dump())
    db.add(s)
    db.commit()
    return story_out(s)
