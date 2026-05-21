"""Admin-only management of PM <-> Family assignments.

A PM can only upload build-plan import files for the families they are
assigned to here. Admins bypass that check entirely.

All write operations require the caller to have the ``Admin`` role.
Read access is granted via the ``pm_family:read`` permission so PMs can
view their own assignments (and the import page can surface them).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_current_user
from app.db.deps import get_db
from app.models.auth.user import User
from app.models.build.family import Family
from app.models.build.family_form_factor import FamilyFormFactor
from app.models.build.pm_family import PMFamily
from app.models.order.build_request import BuildRequest
from app.services.rbac_service import RBACService


router = APIRouter(prefix="/pm-families", tags=["PM Families"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class _UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str | None = None
    email: str | None = None


class _FamilySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str


class PMFamilyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user: _UserSummary
    family: _FamilySummary


class PMFamilyCreate(BaseModel):
    user_id: int
    family_id: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_admin(current_user: User) -> None:
    roles = RBACService.get_user_roles(current_user)
    if "Admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators may modify PM-Family assignments",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[PMFamilyResponse])
def list_pm_families(
    user_id: int | None = None,
    family_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List PM-Family assignments. Optional filters: ``user_id``, ``family_id``.

    Read access is granted to any authenticated user so the import page can
    show PMs their own assignments. Writes remain admin-only.
    """
    query = (
        db.query(PMFamily)
        .options(joinedload(PMFamily.user), joinedload(PMFamily.family))
    )
    if user_id is not None:
        query = query.filter(PMFamily.user_id == user_id)
    if family_id is not None:
        query = query.filter(PMFamily.family_id == family_id)
    rows = query.order_by(PMFamily.id.asc()).all()
    return rows


@router.get("/families", response_model=list[_FamilySummary])
def list_families_lookup(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lightweight families lookup used by the PM-Family management UI."""
    return db.query(Family).order_by(Family.code.asc()).all()


class FamilyCreate(BaseModel):
    code: str
    name: str
    description: str | None = None


@router.post("/families", response_model=_FamilySummary, status_code=status.HTTP_201_CREATED)
def create_family(
    payload: FamilyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new product family. Admin-only."""
    _require_admin(current_user)
    if db.query(Family).filter(Family.code == payload.code).first():
        raise HTTPException(status_code=409, detail="Family code already exists")
    if db.query(Family).filter(Family.name == payload.name).first():
        raise HTTPException(status_code=409, detail="Family name already exists")
    row = Family(code=payload.code, name=payload.name, description=payload.description)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/families/{family_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_family(
    family_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a product family. Admin-only.

    Fails with 409 if any build requests still reference one of this
    family's form-factor mappings. PM assignments, family/form-factor
    mappings, and component-supplier-family rows cascade-delete.
    """
    _require_admin(current_user)

    row = db.query(Family).filter(Family.id == family_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Family not found")

    in_use = (
        db.query(BuildRequest.id)
        .join(FamilyFormFactor, BuildRequest.family_form_factor_id == FamilyFormFactor.id)
        .filter(FamilyFormFactor.family_id == family_id)
        .first()
    )
    if in_use:
        raise HTTPException(
            status_code=409,
            detail="Family is in use by existing build requests and cannot be deleted",
        )

    db.delete(row)
    db.commit()
    return None


@router.post("", response_model=PMFamilyResponse, status_code=status.HTTP_201_CREATED)
def create_pm_family(
    payload: PMFamilyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    if not db.query(User.id).filter(User.id == payload.user_id).first():
        raise HTTPException(status_code=404, detail="User not found")
    if not db.query(Family.id).filter(Family.id == payload.family_id).first():
        raise HTTPException(status_code=404, detail="Family not found")

    existing = (
        db.query(PMFamily)
        .filter(
            PMFamily.user_id == payload.user_id,
            PMFamily.family_id == payload.family_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Assignment already exists")

    row = PMFamily(user_id=payload.user_id, family_id=payload.family_id)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pm_family(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    row = db.query(PMFamily).filter(PMFamily.id == assignment_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(row)
    db.commit()
    return None
