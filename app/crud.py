# app/crud.py
from sqlalchemy.orm import Session
from . import models
from passlib.context import CryptContext
from typing import Optional

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_or_create_tenant(db: Session, name: str):
    t = db.query(models.Tenant).filter(models.Tenant.name == name).first()
    if t:
        return t
    t = models.Tenant(name=name)
    db.add(t); db.commit(); db.refresh(t)
    return t

def create_user(db: Session, username: str, password: str, tenant: models.Tenant, email: Optional[str]=None):
    hashed = pwd_context.hash(password) if password else None
    user = models.User(username=username, hashed_password=hashed, tenant_id=tenant.id, email=email)
    db.add(user); db.commit(); db.refresh(user)
    return user

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def verify_password(plain: str, hashed: str):
    return pwd_context.verify(plain, hashed)

def create_annotation(db: Session, tenant_id: int, ann_in):
    ann = models.Annotation(tenant_id=tenant_id, page=ann_in.page, x=ann_in.x, y=ann_in.y, text=ann_in.text, color=ann_in.color)
    db.add(ann); db.commit(); db.refresh(ann)
    return ann

def list_annotations(db: Session, tenant_id: int, page: int=0):
    return db.query(models.Annotation).filter_by(tenant_id=tenant_id, page=page).all()

def create_service_request(db: Session, tenant_id: int, user_id: int, sr_in):
    sr = models.ServiceRequest(tenant_id=tenant_id, created_by=user_id, subject=sr_in.subject, description=sr_in.description, metadata=sr_in.metadata)
    db.add(sr); db.commit(); db.refresh(sr)
    return sr
