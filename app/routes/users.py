# app/routes/users.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import crud, models, schemas
from ..auth import create_access_token
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/register", response_model=schemas.UserOut)
def register(u: schemas.UserCreate, db: Session = Depends(get_db)):
    tenant = crud.get_or_create_tenant(db, u.tenant_name)
    existing = crud.get_user_by_username(db, u.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    user = crud.create_user(db, username=u.username, password=u.password, tenant=tenant, email=u.email)
    return user

@router.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, form_data.username)
    if not user or not crud.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username, "tenant_id": user.tenant_id})
    return {"access_token": token, "token_type": "bearer"}
