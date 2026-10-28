from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Status = Literal["todo", "in_progress", "done"]
Priority = Literal["low", "medium", "high"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth / users
class RegisterIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)  # bcrypt ignores bytes past 72


class UserOut(ORM):
    id: int
    name: str
    email: EmailStr


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---- tasks
class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    status: Status = "todo"
    assignee_id: Optional[int] = None
    due_date: Optional[date] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    status: Optional[Status] = None
    assignee_id: Optional[int] = None
    due_date: Optional[date] = None


class TaskOut(ORM):
    id: int
    story_id: int
    title: str
    description: str
    status: Status
    assignee_id: Optional[int]
    due_date: Optional[date]
    created_at: datetime


# ---- stories
class StoryIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=5000)
    status: Status = "todo"
    priority: Priority = "medium"
    story_points: Optional[int] = Field(default=None, ge=0, le=100)
    assignee_id: Optional[int] = None


class StoryUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=5000)
    status: Optional[Status] = None
    priority: Optional[Priority] = None
    story_points: Optional[int] = Field(default=None, ge=0, le=100)
    assignee_id: Optional[int] = None


class StoryOut(ORM):
    id: int
    project_id: int
    title: str
    description: str
    status: Status
    priority: Priority
    story_points: Optional[int]
    assignee_id: Optional[int]
    created_at: datetime
    total_tasks: int = 0
    done_tasks: int = 0
    progress: float = 0.0  # 0..1 = done tasks / total tasks


# ---- projects
class ProjectIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=5000)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = Field(default=None, max_length=5000)


class ProjectOut(ORM):
    id: int
    name: str
    description: str
    owner_id: int
    created_at: datetime
    story_count: int = 0
    total_tasks: int = 0
    done_tasks: int = 0
    progress: float = 0.0


# ---- notifications / jobs
class NotificationOut(ORM):
    id: int
    task_id: Optional[int]
    kind: str
    message: str
    is_read: bool
    created_at: datetime


class JobLogOut(ORM):
    id: int
    job_type: str
    task_id: Optional[int]
    status: str
    attempts: int
    error_message: Optional[str]
    created_at: datetime
    finished_at: Optional[datetime]
