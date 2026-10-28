import os
from datetime import date, timedelta

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["JOB_BACKOFF_SECONDS"] = "0"

import pytest
from fastapi.testclient import TestClient

from app import config, models, worker
from app.database import Base, SessionLocal, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


def register(client, email="a@example.com", name="A"):
    r = client.post("/api/auth/register", json={"name": name, "email": email, "password": "password123"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_requires_auth(client):
    assert client.get("/api/projects").status_code == 401


def test_login_and_wrong_password(client):
    register(client)
    ok = client.post("/api/auth/login", data={"username": "a@example.com", "password": "password123"})
    bad = client.post("/api/auth/login", data={"username": "a@example.com", "password": "nope-nope"})
    assert ok.status_code == 200 and bad.status_code == 401


def test_hierarchy_and_progress(client):
    h = register(client)
    p = client.post("/api/projects", json={"name": "P"}, headers=h).json()
    s = client.post(f"/api/projects/{p['id']}/stories", json={"title": "S"}, headers=h).json()
    t1 = client.post(f"/api/stories/{s['id']}/tasks", json={"title": "T1"}, headers=h).json()
    client.post(f"/api/stories/{s['id']}/tasks", json={"title": "T2"}, headers=h)
    client.patch(f"/api/tasks/{t1['id']}", json={"status": "done"}, headers=h)
    assert client.get(f"/api/stories/{s['id']}", headers=h).json()["progress"] == 0.5
    assert client.get(f"/api/projects/{p['id']}", headers=h).json()["progress"] == 0.5


def test_validation_and_cascade_delete(client):
    h = register(client)
    assert client.post("/api/projects", json={"name": ""}, headers=h).status_code == 422
    p = client.post("/api/projects", json={"name": "P"}, headers=h).json()
    s = client.post(f"/api/projects/{p['id']}/stories", json={"title": "S"}, headers=h).json()
    client.post(f"/api/stories/{s['id']}/tasks", json={"title": "T"}, headers=h)
    assert client.patch(f"/api/stories/{s['id']}", json={"status": "bogus"}, headers=h).status_code == 422
    assert client.delete(f"/api/projects/{p['id']}", headers=h).status_code == 204
    assert client.get(f"/api/stories/{s['id']}", headers=h).status_code == 404


def test_only_owner_can_delete_project(client):
    owner, other = register(client), register(client, "b@example.com", "B")
    p = client.post("/api/projects", json={"name": "P"}, headers=owner).json()
    assert client.delete(f"/api/projects/{p['id']}", headers=other).status_code == 403


def _overdue_task(client):
    h = register(client)
    uid = client.get("/api/users/me", headers=h).json()["id"]
    p = client.post("/api/projects", json={"name": "P"}, headers=h).json()
    s = client.post(f"/api/projects/{p['id']}/stories", json={"title": "S"}, headers=h).json()
    client.post(f"/api/stories/{s['id']}/tasks", headers=h, json={
        "title": "Late", "assignee_id": uid, "due_date": str(date.today() - timedelta(days=1))})
    return h


def test_worker_creates_reminder_once(client):
    h = _overdue_task(client)
    assert worker.run_overdue_check()["sent"] == 1
    assert worker.run_overdue_check()["checked"] == 0  # idempotent within the day
    assert len(client.get("/api/notifications", headers=h).json()) == 1


def test_worker_retries_then_marks_failed(client, monkeypatch):
    h = _overdue_task(client)
    monkeypatch.setattr(config, "DELIVERY_FAIL_RATE", 1.0)
    assert worker.run_overdue_check()["failed"] == 1
    log = client.get("/api/jobs/logs", headers=h).json()[0]
    assert log["status"] == "failed" and log["attempts"] == config.JOB_MAX_ATTEMPTS
    # next run succeeds once delivery recovers
    monkeypatch.setattr(config, "DELIVERY_FAIL_RATE", 0.0)
    assert worker.run_overdue_check()["sent"] == 1
