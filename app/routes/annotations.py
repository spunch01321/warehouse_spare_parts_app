# app/routes/annotations.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..auth import get_current_user
from .. import crud, schemas

router = APIRouter(prefix="/annotations", tags=["annotations"])

@router.post("", response_model=schemas.AnnotationOut, status_code=201)
def create_annotation(ann: schemas.AnnotationIn, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    created = crud.create_annotation(db, tenant_id=current_user.tenant_id, ann_in=ann)
    return created

@router.get("", response_model=list[schemas.AnnotationOut])
def list_annotations(page: int = 0, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    anns = crud.list_annotations(db, tenant_id=current_user.tenant_id, page=page)
    return anns
