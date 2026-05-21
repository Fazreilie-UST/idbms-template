from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.core.dependencies import require_permission
from app.models.auth.user import User
from app.models.auth.department import Department


router = APIRouter()


class DepartmentResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    model_config = {"from_attributes": True}


class DepartmentCreate(BaseModel):
    name: str
    description: str | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


@router.get("/", response_model=list[DepartmentResponse])
def list_departments(db: Session = Depends(get_db), _: User = Depends(require_permission("user:read"))):
    return db.query(Department).order_by(Department.id.asc()).all()


@router.post("/", response_model=DepartmentResponse)
def create_department(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("user:create")),
):
    if db.query(Department).filter(Department.name == data.name).first():
        raise HTTPException(status_code=409, detail="Department already exists")
    d = Department(name=data.name, description=data.description)
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


@router.patch("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    data: DepartmentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("user:update")),
):
    d = db.query(Department).filter(Department.id == department_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Department not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(d, k, v)
    db.commit()
    db.refresh(d)
    return d


@router.delete("/{department_id}")
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("user:update")),
):
    d = db.query(Department).filter(Department.id == department_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Department not found")
    db.delete(d)
    db.commit()
    return {"message": "Department deleted"}
