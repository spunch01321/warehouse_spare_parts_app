# app/routes/service.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth import get_current_user
from .. import crud, schemas

router = APIRouter(prefix="/service", tags=["service"])

@router.post("/request", response_model=schemas.ServiceRequestOut, status_code=201)
def request_service(payload: schemas.ServiceRequestIn, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    sr = crud.create_service_request(db, tenant_id=current_user.tenant_id, user_id=current_user.id, sr_in=payload)
    return sr
