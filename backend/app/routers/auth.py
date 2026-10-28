from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .. import auth, models, schemas
from ..database import get_db

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/register", response_model=schemas.TokenOut, status_code=201)
def register(data: schemas.RegisterIn, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.query(models.User).filter(models.User.email == email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = models.User(name=data.name.strip(), email=email, password_hash=auth.hash_password(data.password))
    db.add(user)
    db.commit()
    return schemas.TokenOut(access_token=auth.create_access_token(user.id), user=user)


@router.post("/auth/login", response_model=schemas.TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2 form uses the field name "username"; we treat it as the email.
    user = auth.authenticate(db, form.username, form.password)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return schemas.TokenOut(access_token=auth.create_access_token(user.id), user=user)


@router.get("/users/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(auth.get_current_user)):
    return user


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db), _: models.User = Depends(auth.get_current_user)):
    """Team members, used for assignee dropdowns."""
    return db.query(models.User).order_by(models.User.name).all()
