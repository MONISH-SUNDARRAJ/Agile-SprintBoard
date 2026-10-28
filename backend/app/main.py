import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config, models  # noqa: F401  (models must be imported so tables register)
from .database import Base, engine
from .routers import auth, notifications, projects, work
from .worker import run_overdue_check

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_overdue_check, "interval", minutes=config.OVERDUE_CHECK_MINUTES,
                      id="overdue_check", max_instances=1, coalesce=True)
    scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown(wait=False)


app = FastAPI(
    title="SprintBoard API",
    description="Agile project tracking: Project -> User Story -> Task. "
                "Click Authorize and log in with email + password to try protected endpoints.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

for r in (auth.router, projects.router, work.router, notifications.router):
    app.include_router(r)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
