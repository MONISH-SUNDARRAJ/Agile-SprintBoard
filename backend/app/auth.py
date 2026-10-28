from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from . import config, models
from .database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


# Keeps login timing similar whether or not the email exists.
_DUMMY_HASH = hash_password("not-a-real-password")


def create_access_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=config.ACCESS_TOKEN_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": exp}, config.SECRET_KEY, algorithm=ALGORITHM)


def authenticate(db: Session, email: str, password: str) -> models.User | None:
    user = db.query(models.User).filter(models.User.email == email.lower()).first()
    ok = verify_password(password, user.password_hash if user else _DUMMY_HASH)
    return user if user and ok else None


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    err = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token",
                        headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, config.SECRET_KEY, algorithms=[ALGORITHM])
        user = db.get(models.User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise err
    if not user:
        raise err
    return user
