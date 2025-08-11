# app/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    roles = Column(String, default="user")
    created_at = Column(DateTime, default=datetime.utcnow)
    tenant = relationship("Tenant")

class Annotation(Base):
    __tablename__ = "annotations"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    page = Column(Integer, default=0)
    x = Column(Integer)
    y = Column(Integer)
    text = Column(Text)
    color = Column(String, default="#FF0000")
    created_at = Column(DateTime, default=datetime.utcnow)

class ServiceRequest(Base):
    __tablename__ = "service_requests"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    subject = Column(String, nullable=False)
    description = Column(Text)
    metadata = Column(JSON, default={})
    status = Column(String, default="open")
    created_at = Column(DateTime, default=datetime.utcnow)
