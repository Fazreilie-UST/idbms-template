"""Hierarchical Components / Suppliers / Families administration.

Exposes a single tree endpoint plus per-pair mutation endpoints used by the
admin DB Tables page. Writes are admin-only; reads are gated on
``build_plan:read``.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, require_permission
from app.db.deps import get_db
from app.models.auth.user import User
from app.models.build.component import Component
from app.models.build.component_supplier import ComponentSupplier
from app.models.build.component_supplier_family import ComponentSupplierFamily
from app.models.build.family import Family
from app.models.build.supplier import Supplier
from app.services.rbac_service import RBACService


router = APIRouter(prefix="/component-suppliers", tags=["Component Suppliers"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class FamilyMini(BaseModel):
    id: int
    code: str
    name: str
    model_config = {"from_attributes": True}


class SupplierWithFamilies(BaseModel):
    id: int
    name: str
    families: list[FamilyMini] = Field(default_factory=list)


class ComponentTreeNode(BaseModel):
    id: int
    name: str
    suppliers: list[SupplierWithFamilies] = Field(default_factory=list)


class AddSupplierPayload(BaseModel):
    supplier_id: int
    family_ids: list[int] = Field(default_factory=list)


class SetFamiliesPayload(BaseModel):
    family_ids: list[int] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_admin(user: User) -> None:
    roles = RBACService.get_user_roles(user)
    if "Admin" not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators may modify this resource",
        )


def _validate_families(db: Session, family_ids: list[int]) -> list[Family]:
    if not family_ids:
        return []
    rows = db.query(Family).filter(Family.id.in_(family_ids)).all()
    found = {r.id for r in rows}
    missing = [fid for fid in family_ids if fid not in found]
    if missing:
        raise HTTPException(
            status_code=404, detail=f"Unknown family ids: {missing}"
        )
    return rows


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/tree", response_model=list[ComponentTreeNode])
def get_tree(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    """Return components with their suppliers and the families each supplies."""
    components = db.query(Component).order_by(Component.name.asc()).all()
    pairs = db.query(ComponentSupplier).all()
    suppliers_by_id = {s.id: s for s in db.query(Supplier).all()}

    family_rows = (
        db.query(
            ComponentSupplierFamily.component_id,
            ComponentSupplierFamily.supplier_id,
            Family.id,
            Family.code,
            Family.name,
        )
        .join(Family, Family.id == ComponentSupplierFamily.family_id)
        .all()
    )

    # Group family entries by (component_id, supplier_id)
    fam_map: dict[tuple[int, int], list[FamilyMini]] = {}
    for component_id, supplier_id, fid, fcode, fname in family_rows:
        fam_map.setdefault((component_id, supplier_id), []).append(
            FamilyMini(id=fid, code=fcode, name=fname)
        )
    for key in fam_map:
        fam_map[key].sort(key=lambda f: f.code.lower())

    # Group suppliers by component
    sup_map: dict[int, list[SupplierWithFamilies]] = {}
    for pair in pairs:
        sup = suppliers_by_id.get(pair.supplier_id)
        if not sup:
            continue
        sup_map.setdefault(pair.component_id, []).append(
            SupplierWithFamilies(
                id=sup.id,
                name=sup.name,
                families=fam_map.get((pair.component_id, pair.supplier_id), []),
            )
        )
    for key in sup_map:
        sup_map[key].sort(key=lambda s: s.name.lower())

    return [
        ComponentTreeNode(
            id=c.id, name=c.name, suppliers=sup_map.get(c.id, [])
        )
        for c in components
    ]


@router.post(
    "/{component_id}/suppliers",
    response_model=SupplierWithFamilies,
    status_code=status.HTTP_201_CREATED,
)
def add_supplier_to_component(
    component_id: int,
    payload: AddSupplierPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Link a supplier to a component and optionally seed its supplied families."""
    _require_admin(current_user)

    component = db.query(Component).filter(Component.id == component_id).first()
    if not component:
        raise HTTPException(status_code=404, detail="Component not found")

    supplier = db.query(Supplier).filter(Supplier.id == payload.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    existing_pair = (
        db.query(ComponentSupplier)
        .filter(
            ComponentSupplier.component_id == component_id,
            ComponentSupplier.supplier_id == payload.supplier_id,
        )
        .first()
    )
    if existing_pair:
        raise HTTPException(
            status_code=409,
            detail="Supplier is already linked to this component",
        )

    families = _validate_families(db, payload.family_ids)

    db.add(
        ComponentSupplier(
            component_id=component_id, supplier_id=payload.supplier_id
        )
    )
    db.flush()
    for fam in families:
        db.add(
            ComponentSupplierFamily(
                component_id=component_id,
                supplier_id=payload.supplier_id,
                family_id=fam.id,
            )
        )
    db.commit()

    return SupplierWithFamilies(
        id=supplier.id,
        name=supplier.name,
        families=sorted(
            (FamilyMini(id=f.id, code=f.code, name=f.name) for f in families),
            key=lambda f: f.code.lower(),
        ),
    )


@router.delete(
    "/{component_id}/suppliers/{supplier_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_supplier_from_component(
    component_id: int,
    supplier_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)

    pair = (
        db.query(ComponentSupplier)
        .filter(
            ComponentSupplier.component_id == component_id,
            ComponentSupplier.supplier_id == supplier_id,
        )
        .first()
    )
    if not pair:
        raise HTTPException(status_code=404, detail="Link not found")

    # Family rows cascade via composite FK ON DELETE CASCADE.
    db.delete(pair)
    db.commit()
    return None


@router.put(
    "/{component_id}/suppliers/{supplier_id}/families",
    response_model=SupplierWithFamilies,
)
def set_supplier_families(
    component_id: int,
    supplier_id: int,
    payload: SetFamiliesPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Replace the family set for a (component, supplier) pair."""
    _require_admin(current_user)

    pair = (
        db.query(ComponentSupplier)
        .filter(
            ComponentSupplier.component_id == component_id,
            ComponentSupplier.supplier_id == supplier_id,
        )
        .first()
    )
    if not pair:
        raise HTTPException(status_code=404, detail="Link not found")

    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    families = _validate_families(db, payload.family_ids)

    db.query(ComponentSupplierFamily).filter(
        ComponentSupplierFamily.component_id == component_id,
        ComponentSupplierFamily.supplier_id == supplier_id,
    ).delete(synchronize_session=False)

    for fam in families:
        db.add(
            ComponentSupplierFamily(
                component_id=component_id,
                supplier_id=supplier_id,
                family_id=fam.id,
            )
        )
    db.commit()

    return SupplierWithFamilies(
        id=supplier.id,
        name=supplier.name,
        families=sorted(
            (FamilyMini(id=f.id, code=f.code, name=f.name) for f in families),
            key=lambda f: f.code.lower(),
        ),
    )
