# app/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str
    tenant_id: int

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str]
    tenant_name: str

class UserOut(BaseModel):
    id: int
    username: str
    email: Optional[str]
    tenant_id: int

    class Config:
        orm_mode = True

class AnnotationIn(BaseModel):
    page: int
    x: int
    y: int
    text: str
    color: Optional[str] = "#FF0000"

class AnnotationOut(AnnotationIn):
    id: int
    created_at: Optional[str]

    class Config:
        orm_mode = True

class ServiceRequestIn(BaseModel):
    subject: str
    description: str
    metadata: Optional[Dict] = {}

class ServiceRequestOut(ServiceRequestIn):
    id: int
    status: str
    created_at: Optional[str]

    class Config:
        orm_mode = True
