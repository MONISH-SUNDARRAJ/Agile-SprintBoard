import os
import secrets
import logging

from dotenv import load_dotenv

load_dotenv()  # reads backend/.env if present

log = logging.getLogger("sprintboard")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Safe fallback for local dev: tokens become invalid on restart.
    SECRET_KEY = secrets.token_urlsafe(48)
    log.warning("SECRET_KEY not set; using a random key for this run only.")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sprintboard.db")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "60"))
OVERDUE_CHECK_MINUTES = int(os.getenv("OVERDUE_CHECK_MINUTES", "5"))
JOB_MAX_ATTEMPTS = int(os.getenv("JOB_MAX_ATTEMPTS", "3"))
JOB_BACKOFF_SECONDS = float(os.getenv("JOB_BACKOFF_SECONDS", "2"))
DELIVERY_FAIL_RATE = float(os.getenv("DELIVERY_FAIL_RATE", "0"))
