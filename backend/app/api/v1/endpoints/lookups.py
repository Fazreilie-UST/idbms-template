"""
CRUD endpoints for dictionary / lookup tables managed in the admin panel:
  - Forwarders
  - Recipient Groups (with members)
  - Build Notes
  - Support Activities
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from app.db.deps import get_db
from app.core.dependencies import require_permission
from app.models.auth.user import User
from app.models.order.forwarder import Forwarder
from app.models.build.build_plan import BuildNote, SupportActivity, BuildPlanBuildDesc
from app.models.build.form_factor import FormFactor
from app.models.build.silicon_stepping import SiliconStepping
from app.models.build.component import Component
from app.models.build.supplier import Supplier
from app.models.order.address import Address
from app.models.build.warehouse import Warehouse


# =========================================================================
# Schemas
# =========================================================================

class _NameBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class _NameUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)


class IdName(BaseModel):
    id: int
    name: str
    model_config = {"from_attributes": True}


class UserMini(BaseModel):
    id: int
    full_name: str | None = None
    email: str | None = None
    employee_id: str | None = None
    model_config = {"from_attributes": True}


class BuildNoteResponse(BaseModel):
    id: int
    notes: str
    model_config = {"from_attributes": True}


class BuildNoteCreate(BaseModel):
    notes: str = Field(..., min_length=1)


class BuildNoteUpdate(BaseModel):
    notes: str | None = Field(default=None, min_length=1)


# =========================================================================
# Forwarders
# =========================================================================

forwarders_router = APIRouter()


@forwarders_router.get("/", response_model=list[IdName])
def list_forwarders(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("shipping:read")),
):
    return db.query(Forwarder).order_by(Forwarder.name.asc()).all()


@forwarders_router.post("/", response_model=IdName)
def create_forwarder(
    data: _NameBase,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("shipping:create")),
):
    if db.query(Forwarder).filter(Forwarder.name == data.name).first():
        raise HTTPException(status_code=409, detail="Forwarder already exists")
    obj = Forwarder(name=data.name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@forwarders_router.patch("/{forwarder_id}", response_model=IdName)
def update_forwarder(
    forwarder_id: int,
    data: _NameUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("shipping:update")),
):
    obj = db.query(Forwarder).filter(Forwarder.id == forwarder_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    if data.name is not None:
        if db.query(Forwarder).filter(Forwarder.name == data.name, Forwarder.id != forwarder_id).first():
            raise HTTPException(status_code=409, detail="Name already in use")
        obj.name = data.name
    db.commit()
    db.refresh(obj)
    return obj


@forwarders_router.delete("/{forwarder_id}")
def delete_forwarder(
    forwarder_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("shipping:update")),
):
    obj = db.query(Forwarder).filter(Forwarder.id == forwarder_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Forwarder not found")
    try:
        db.delete(obj)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Forwarder is referenced by existing shipments")
    return {"message": "Forwarder deleted"}


# =========================================================================
# Build Notes
# =========================================================================

build_notes_router = APIRouter()


@build_notes_router.get("/", response_model=list[BuildNoteResponse])
def list_build_notes(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    return db.query(BuildNote).order_by(BuildNote.id.asc()).all()


@build_notes_router.post("/", response_model=BuildNoteResponse)
def create_build_note(
    data: BuildNoteCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:create")),
):
    if db.query(BuildNote).filter(BuildNote.notes == data.notes).first():
        raise HTTPException(status_code=409, detail="Build note already exists")
    obj = BuildNote(notes=data.notes)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@build_notes_router.patch("/{note_id}", response_model=BuildNoteResponse)
def update_build_note(
    note_id: int,
    data: BuildNoteUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:update")),
):
    obj = db.query(BuildNote).filter(BuildNote.id == note_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Build note not found")
    if data.notes is not None:
        if db.query(BuildNote).filter(BuildNote.notes == data.notes, BuildNote.id != note_id).first():
            raise HTTPException(status_code=409, detail="Note text already in use")
        obj.notes = data.notes
    db.commit()
    db.refresh(obj)
    return obj


@build_notes_router.delete("/{note_id}")
def delete_build_note(
    note_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:update")),
):
    obj = db.query(BuildNote).filter(BuildNote.id == note_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Build note not found")
    try:
        db.delete(obj)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Build note is referenced by existing build plans")
    return {"message": "Build note deleted"}


class MergeResponse(BaseModel):
    primary_id: int
    duplicate_id: int
    transferred: dict[str, int] = {}
    deleted_conflicts: dict[str, int] = {}


@build_notes_router.post("/{primary_id}/merge/{duplicate_id}", response_model=MergeResponse)
def merge_build_notes(
    primary_id: int,
    duplicate_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:update")),
):
    """Merge ``duplicate_id`` into ``primary_id``.

    All references to the duplicate build note are repointed to the primary,
    then the duplicate row is deleted. Rows that would violate uniqueness
    constraints (same support activity / build plan already linked to the
    primary) are dropped instead of repointed.
    """
    if primary_id == duplicate_id:
        raise HTTPException(status_code=400, detail="Cannot merge a record into itself")

    primary = db.query(BuildNote).filter(BuildNote.id == primary_id).first()
    duplicate = db.query(BuildNote).filter(BuildNote.id == duplicate_id).first()
    if not primary or not duplicate:
        raise HTTPException(status_code=404, detail="One or both build notes not found")

    transferred: dict[str, int] = {}
    deleted: dict[str, int] = {}

    try:
        # support_activity_build_notes -- unique on (support_activity_id, build_note_id)
        del_sa = db.execute(
            text(
                """
                DELETE FROM support_activity_build_notes
                WHERE build_note_id = :dup
                  AND support_activity_id IN (
                    SELECT support_activity_id FROM support_activity_build_notes
                    WHERE build_note_id = :pri
                  )
                """
            ),
            {"dup": duplicate_id, "pri": primary_id},
        )
        deleted["support_activity_build_notes"] = del_sa.rowcount or 0
        upd_sa = db.execute(
            text(
                "UPDATE support_activity_build_notes SET build_note_id = :pri WHERE build_note_id = :dup"
            ),
            {"dup": duplicate_id, "pri": primary_id},
        )
        transferred["support_activity_build_notes"] = upd_sa.rowcount or 0

        # build_plan_build_notes -- unique on (build_plan_id, build_note_id)
        del_bp = db.execute(
            text(
                """
                DELETE FROM build_plan_build_notes
                WHERE build_note_id = :dup
                  AND build_plan_id IN (
                    SELECT build_plan_id FROM build_plan_build_notes
                    WHERE build_note_id = :pri
                  )
                """
            ),
            {"dup": duplicate_id, "pri": primary_id},
        )
        deleted["build_plan_build_notes"] = del_bp.rowcount or 0
        upd_bp = db.execute(
            text(
                "UPDATE build_plan_build_notes SET build_note_id = :pri WHERE build_note_id = :dup"
            ),
            {"dup": duplicate_id, "pri": primary_id},
        )
        transferred["build_plan_build_notes"] = upd_bp.rowcount or 0

        db.delete(duplicate)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Merge failed: {e.orig}") from e

    return MergeResponse(
        primary_id=primary_id,
        duplicate_id=duplicate_id,
        transferred=transferred,
        deleted_conflicts=deleted,
    )


# =========================================================================
# Support Activities
# =========================================================================

support_activities_router = APIRouter()


@support_activities_router.get("/", response_model=list[IdName])
def list_support_activities(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    return db.query(SupportActivity).order_by(SupportActivity.name.asc()).all()


@support_activities_router.post("/", response_model=IdName)
def create_support_activity(
    data: _NameBase,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:create")),
):
    if db.query(SupportActivity).filter(SupportActivity.name == data.name).first():
        raise HTTPException(status_code=409, detail="Support activity already exists")
    obj = SupportActivity(name=data.name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@support_activities_router.patch("/{activity_id}", response_model=IdName)
def update_support_activity(
    activity_id: int,
    data: _NameUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:update")),
):
    obj = db.query(SupportActivity).filter(SupportActivity.id == activity_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Support activity not found")
    if data.name is not None:
        if db.query(SupportActivity).filter(
            SupportActivity.name == data.name, SupportActivity.id != activity_id
        ).first():
            raise HTTPException(status_code=409, detail="Name already in use")
        obj.name = data.name
    db.commit()
    db.refresh(obj)
    return obj


@support_activities_router.delete("/{activity_id}")
def delete_support_activity(
    activity_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:update")),
):
    obj = db.query(SupportActivity).filter(SupportActivity.id == activity_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Support activity not found")
    try:
        db.delete(obj)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Support activity is referenced by existing build plans")
    return {"message": "Support activity deleted"}


# =========================================================================
# Generic simple "name-only" CRUD builder (Form Factor, Silicon Stepping,
# Component, Supplier). Reads use ``build_plan:read``; writes require
# ``Admin`` role via ``require_admin``.
# =========================================================================

from app.core.dependencies import get_current_user
from app.services.rbac_service import RBACService


def _require_admin(user: User) -> None:
    roles = RBACService.get_user_roles(user)
    if "Admin" not in roles:
        raise HTTPException(
            status_code=403,
            detail="Only administrators may modify this resource",
        )


def _make_name_router(model, *, label: str, fk_error: str):
    """Build a CRUD router for a ``{id, name}`` reference model."""
    r = APIRouter()

    @r.get("/", response_model=list[IdName])
    def _list(
        db: Session = Depends(get_db),
        _: User = Depends(require_permission("build_plan:read")),
    ):
        return db.query(model).order_by(model.name.asc()).all()

    @r.post("/", response_model=IdName)
    def _create(
        data: _NameBase,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        _require_admin(current_user)
        if db.query(model).filter(model.name == data.name).first():
            raise HTTPException(status_code=409, detail=f"{label} already exists")
        obj = model(name=data.name)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @r.patch("/{obj_id}", response_model=IdName)
    def _update(
        obj_id: int,
        data: _NameUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        _require_admin(current_user)
        obj = db.query(model).filter(model.id == obj_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail=f"{label} not found")
        if data.name is not None:
            if db.query(model).filter(model.name == data.name, model.id != obj_id).first():
                raise HTTPException(status_code=409, detail="Name already in use")
            obj.name = data.name
        db.commit()
        db.refresh(obj)
        return obj

    @r.delete("/{obj_id}")
    def _delete(
        obj_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        _require_admin(current_user)
        obj = db.query(model).filter(model.id == obj_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail=f"{label} not found")
        try:
            db.delete(obj)
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail=fk_error)
        return {"message": f"{label} deleted"}

    return r


form_factors_router = _make_name_router(
    FormFactor, label="Form Factor", fk_error="Form factor is referenced by existing records"
)
silicon_steppings_router = _make_name_router(
    SiliconStepping, label="Silicon Stepping", fk_error="Silicon stepping is referenced by existing records"
)
components_router = _make_name_router(
    Component, label="Component", fk_error="Component is referenced by existing records"
)
suppliers_router = _make_name_router(
    Supplier, label="Supplier", fk_error="Supplier is referenced by existing records"
)


# =========================================================================
# Build Descriptions (BuildPlanBuildDesc): {id, support_activity_id, description}
# =========================================================================

class BuildDescriptionResponse(BaseModel):
    id: int
    support_activity_id: int
    description: str
    support_activity_name: str | None = None
    model_config = {"from_attributes": True}


class BuildDescriptionCreate(BaseModel):
    support_activity_id: int
    description: str = Field(..., min_length=1)


class BuildDescriptionUpdate(BaseModel):
    support_activity_id: int | None = None
    description: str | None = Field(default=None, min_length=1)


build_descriptions_router = APIRouter()


@build_descriptions_router.get("/", response_model=list[BuildDescriptionResponse])
def list_build_descriptions(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    rows = (
        db.query(BuildPlanBuildDesc)
        .options(joinedload(BuildPlanBuildDesc.support_activity))
        .order_by(BuildPlanBuildDesc.id.asc())
        .all()
    )
    return [
        BuildDescriptionResponse(
            id=r.id,
            support_activity_id=r.support_activity_id,
            description=r.description,
            support_activity_name=r.support_activity.name if r.support_activity else None,
        )
        for r in rows
    ]


@build_descriptions_router.post("/", response_model=BuildDescriptionResponse)
def create_build_description(
    data: BuildDescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    if not db.query(SupportActivity).filter(SupportActivity.id == data.support_activity_id).first():
        raise HTTPException(status_code=404, detail="Support activity not found")
    if db.query(BuildPlanBuildDesc).filter(
        BuildPlanBuildDesc.support_activity_id == data.support_activity_id,
        BuildPlanBuildDesc.description == data.description,
    ).first():
        raise HTTPException(status_code=409, detail="Build description already exists for this activity")
    obj = BuildPlanBuildDesc(
        support_activity_id=data.support_activity_id,
        description=data.description,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return BuildDescriptionResponse(
        id=obj.id,
        support_activity_id=obj.support_activity_id,
        description=obj.description,
        support_activity_name=obj.support_activity.name if obj.support_activity else None,
    )


@build_descriptions_router.patch("/{obj_id}", response_model=BuildDescriptionResponse)
def update_build_description(
    obj_id: int,
    data: BuildDescriptionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    obj = db.query(BuildPlanBuildDesc).filter(BuildPlanBuildDesc.id == obj_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Build description not found")
    payload = data.model_dump(exclude_unset=True)
    if "support_activity_id" in payload and payload["support_activity_id"] is not None:
        if not db.query(SupportActivity).filter(SupportActivity.id == payload["support_activity_id"]).first():
            raise HTTPException(status_code=404, detail="Support activity not found")
        obj.support_activity_id = payload["support_activity_id"]
    if "description" in payload and payload["description"] is not None:
        obj.description = payload["description"]
    db.commit()
    db.refresh(obj)
    return BuildDescriptionResponse(
        id=obj.id,
        support_activity_id=obj.support_activity_id,
        description=obj.description,
        support_activity_name=obj.support_activity.name if obj.support_activity else None,
    )


@build_descriptions_router.delete("/{obj_id}")
def delete_build_description(
    obj_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    obj = db.query(BuildPlanBuildDesc).filter(BuildPlanBuildDesc.id == obj_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Build description not found")
    try:
        db.delete(obj)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Build description is referenced by existing records")
    return {"message": "Build description deleted"}


# =========================================================================
# Addresses
# =========================================================================

class AddressResponse(BaseModel):
    id: int
    label: str | None = None
    user_id: int | None = None
    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    notes: str | None = None
    is_default: bool = False
    model_config = {"from_attributes": True}


class AddressCreate(BaseModel):
    label: str | None = None
    user_id: int | None = None
    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    notes: str | None = None
    is_default: bool = False


class AddressUpdate(BaseModel):
    label: str | None = None
    user_id: int | None = None
    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    postal_code: str | None = None
    notes: str | None = None
    is_default: bool | None = None


addresses_router = APIRouter()


@addresses_router.get("/", response_model=list[AddressResponse])
def list_addresses(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("shipping:read")),
):
    return db.query(Address).order_by(Address.id.asc()).all()


@addresses_router.post("/", response_model=AddressResponse)
def create_address(
    data: AddressCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("shipping:create")),
):
    obj = Address(**data.model_dump(exclude_unset=True))
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@addresses_router.patch("/{obj_id}", response_model=AddressResponse)
def update_address(
    obj_id: int,
    data: AddressUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("shipping:update")),
):
    obj = db.query(Address).filter(Address.id == obj_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Address not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@addresses_router.delete("/{obj_id}")
def delete_address(
    obj_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("shipping:update")),
):
    obj = db.query(Address).filter(Address.id == obj_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Address not found")
    try:
        db.delete(obj)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Address is referenced by existing records")
    return {"message": "Address deleted"}


# =========================================================================
# Warehouses
# =========================================================================

class WarehouseResponse(BaseModel):
    id: int
    name: str
    notes: str | None = None
    model_config = {"from_attributes": True}


class WarehouseCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    notes: str | None = None


class WarehouseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    notes: str | None = None


warehouses_router = APIRouter()


@warehouses_router.get("/", response_model=list[WarehouseResponse])
def list_warehouses(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("build_plan:read")),
):
    return db.query(Warehouse).order_by(Warehouse.name.asc()).all()


@warehouses_router.post("/", response_model=WarehouseResponse)
def create_warehouse(
    data: WarehouseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    if db.query(Warehouse).filter(Warehouse.name == data.name).first():
        raise HTTPException(status_code=409, detail="Warehouse already exists")
    obj = Warehouse(name=data.name, notes=data.notes)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@warehouses_router.patch("/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse(
    warehouse_id: int,
    data: WarehouseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    obj = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    payload = data.model_dump(exclude_unset=True)
    if "name" in payload and payload["name"] is not None:
        if db.query(Warehouse).filter(
            Warehouse.name == payload["name"], Warehouse.id != warehouse_id
        ).first():
            raise HTTPException(status_code=409, detail="Name already in use")
        obj.name = payload["name"]
    if "notes" in payload:
        obj.notes = payload["notes"]
    db.commit()
    db.refresh(obj)
    return obj


@warehouses_router.delete("/{warehouse_id}")
def delete_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_admin(current_user)
    obj = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Warehouse not found")
    try:
        db.delete(obj)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Warehouse is referenced by existing records")
    return {"message": "Warehouse deleted"}

