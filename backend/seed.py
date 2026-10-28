"""Demo data: python seed.py   (creates 3 users, a project, stories, tasks incl. overdue ones)"""
from datetime import date, timedelta

from app import models
from app.auth import hash_password
from app.database import Base, SessionLocal, engine

Base.metadata.create_all(engine)
db = SessionLocal()
if db.query(models.User).count():
    raise SystemExit("Database already has data; delete sprintboard.db to reseed.")

users = [models.User(name=n, email=e, password_hash=hash_password("password123"))
         for n, e in [("Asha Rao", "asha@example.com"), ("Ravi Kumar", "ravi@example.com"),
                      ("Meera Iyer", "meera@example.com")]]
db.add_all(users)
db.commit()
asha, ravi, meera = users

p = models.Project(name="College Placement Portal", description="Portal for students to apply to drives.",
                   owner_id=asha.id)
db.add(p)
db.commit()
today = date.today()
stories = [
    models.UserStory(project_id=p.id, title="As a student, I can upload my resume", status="in_progress",
                     priority="high", story_points=5, assignee_id=ravi.id),
    models.UserStory(project_id=p.id, title="As a recruiter, I can view applicants", status="todo",
                     priority="medium", story_points=8, assignee_id=meera.id),
    models.UserStory(project_id=p.id, title="As a student, I can reset my password", status="done",
                     priority="low", story_points=3, assignee_id=asha.id),
]
db.add_all(stories)
db.commit()
db.add_all([
    models.Task(story_id=stories[0].id, title="Design upload form", status="done", assignee_id=ravi.id),
    models.Task(story_id=stories[0].id, title="Write file validation", status="in_progress",
                assignee_id=ravi.id, due_date=today - timedelta(days=2)),  # overdue
    models.Task(story_id=stories[0].id, title="Store files securely", status="todo",
                assignee_id=meera.id, due_date=today - timedelta(days=1)),  # overdue
    models.Task(story_id=stories[1].id, title="Applicant list API", status="todo",
                assignee_id=meera.id, due_date=today + timedelta(days=5)),
    models.Task(story_id=stories[2].id, title="Reset email template", status="done", assignee_id=asha.id),
])
db.commit()
print("Seeded. Log in with asha@example.com / password123")
