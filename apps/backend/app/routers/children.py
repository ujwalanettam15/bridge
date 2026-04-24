from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid

from app.models import Child
from app.core.database import get_db

router = APIRouter(prefix="/children", tags=["children"])


class ChildCreate(BaseModel):
    name: str
    age: float
    behavior_profile: dict = {}
    preferred_symbols: list = []


class ChildUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[float] = None
    behavior_profile: Optional[dict] = None
    preferred_symbols: Optional[list] = None


@router.post("/")
def create_child(payload: ChildCreate, db=Depends(get_db)):
    child = Child(
        id=str(uuid.uuid4()),
        name=payload.name,
        age=payload.age,
        behavior_profile=payload.behavior_profile,
        preferred_symbols=payload.preferred_symbols,
    )
    db.add(child)
    db.commit()
    db.refresh(child)
    return child


@router.get("/{child_id}")
def get_child(child_id: str, db=Depends(get_db)):
    child = db.query(Child).filter(Child.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    return child


@router.patch("/{child_id}")
def update_child(child_id: str, payload: ChildUpdate, db=Depends(get_db)):
    child = db.query(Child).filter(Child.id == child_id).first()
    if not child:
        raise HTTPException(status_code=404, detail="Child not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(child, field, value)
    db.commit()
    db.refresh(child)
    return child


@router.get("/")
def list_children(db=Depends(get_db)):
    return db.query(Child).all()
