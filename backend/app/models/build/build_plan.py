import enum

from ..base import (
    Base,
    Column,
    Integer,
    String,
    ForeignKey,
    relationship,
    Enum,
    DateTime,
    UniqueConstraint,
    Index,
)


# ==========================
# ENUMS
# ==========================

class BuildPlanStatus(str, enum.Enum):
    plan = "Plan"
    hold = "Hold"
    done = "Done"
    cancelled = "Cancelled"
    new = "New"


# ==========================
# SUPPORT ACTIVITY
# ==========================

class SupportActivity(Base):
    __tablename__ = "support_activities"

    id = Column(Integer, primary_key=True)

    name = Column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )


# ==========================
# BUILD DESCRIPTION
# ==========================

class BuildPlanBuildDesc(Base):
    __tablename__ = "build_plan_build_descs"

    id = Column(Integer, primary_key=True)

    support_activity_id = Column(
        Integer,
        ForeignKey("support_activities.id"),
        nullable=False,
    )

    description = Column(String, nullable=False)

    support_activity = relationship("SupportActivity")

    __table_args__ = (
        UniqueConstraint(
            "support_activity_id",
            "description",
            name="uq_build_desc_per_activity",
        ),
    )


# ==========================
# BUILD NOTE
# ==========================

class BuildNote(Base):
    __tablename__ = "build_notes"

    id = Column(Integer, primary_key=True)

    notes = Column(
        String,
        nullable=False,
        unique=True,
    )


# ==========================
# SUPPORT ACTIVITY ↔ BUILD NOTE
# ==========================

class SupportActivityBuildNote(Base):
    __tablename__ = "support_activity_build_notes"

    id = Column(Integer, primary_key=True)

    support_activity_id = Column(
        Integer,
        ForeignKey("support_activities.id", ondelete="CASCADE"),
        nullable=False,
    )

    build_note_id = Column(
        Integer,
        ForeignKey("build_notes.id", ondelete="CASCADE"),
        nullable=False,
    )

    support_activity = relationship("SupportActivity")
    build_note = relationship("BuildNote")

    __table_args__ = (
        UniqueConstraint(
            "support_activity_id",
            "build_note_id",
            name="uq_support_activity_build_note",
        ),
    )


# ==========================
# MAIN BUILD PLAN
# ==========================

class BuildPlan(Base):
    __tablename__ = "build_plans"

    id = Column(Integer, primary_key=True)

    family_form_factor_id = Column(
        Integer,
        ForeignKey("family_form_factors.id"),
        nullable=False,
    )

    support_activity_id = Column(
        Integer,
        ForeignKey("support_activities.id"),
        nullable=False,
    )

    status = Column(
        Enum(BuildPlanStatus),
        nullable=False,
    )

    build_description_id = Column(
        Integer,
        ForeignKey("build_plan_build_descs.id"),
        nullable=False,
    )

    config_number_id = Column(
        Integer,
        ForeignKey("config_numbers.id"),
        nullable=False,
    )

    # Pointer to the latest revision (i.e. the one whose snapshot this row
    # currently mirrors). Nullable only briefly during the insert flow; in
    # steady state every BuildPlan has at least one revision.
    latest_revision_id = Column(
        Integer,
        ForeignKey(
            "build_plan_revisions.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_build_plans_latest_revision_id",
        ),
        nullable=True,
        index=True,
    )

    # First/last import file ever processed against this config (in
    # chronological order, not arrival order). ON DELETE SET NULL so deleting
    # an import record does not cascade-delete the canonical build plan.
    first_seen_file_id = Column(
        Integer,
        ForeignKey("build_plan_import_files.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_seen_file_id = Column(
        Integer,
        ForeignKey("build_plan_import_files.id", ondelete="SET NULL"),
        nullable=True,
    )

    latest_revision = relationship(
        "BuildPlanRevision",
        foreign_keys=[latest_revision_id],
        post_update=True,
    )
    first_seen_file = relationship(
        "BuildPlanImportFile", foreign_keys=[first_seen_file_id]
    )
    last_seen_file = relationship(
        "BuildPlanImportFile", foreign_keys=[last_seen_file_id]
    )

    product_code = Column(String)
    mm_number = Column(String)
    ta_number = Column(String)
    pba_number = Column(String)
    as_number = Column(String)

    special_instruction = Column(String)

    build_start_date = Column(DateTime)
    ship_date = Column(DateTime)

    required_quantity = Column(Integer)
    estimated_yield = Column(Integer)
    build_start_quantity = Column(Integer)

    # Calendar year derived from the config number (``<FamilyCode><YY><WW>``).
    # Denormalised onto the row so dashboards can filter / group by year
    # without re-parsing the string each time. Indexed for "build plans by
    # year" queries.
    year = Column(Integer, nullable=True, index=True)

    # ISO work-week derived from the config number (``<FamilyCode><YY><WW>``).
    # Denormalised alongside ``year`` so the Milestone Builds Timeline and
    # similar widgets can bucket by (year, work_week) without re-parsing the
    # config string.
    work_week = Column(Integer, nullable=True, index=True)

    support_activity = relationship("SupportActivity")

    build_description = relationship("BuildPlanBuildDesc")

    build_note_links = relationship(
        "BuildPlanBuildNote",
        back_populates="build_plan",
        cascade="all, delete-orphan",
    )

    components = relationship(
        "BuildPlanComponent",
        back_populates="build_plan",
        cascade="all, delete-orphan",
    )

    tests = relationship(
        "BuildPlanTest",
        back_populates="build_plan",
        cascade="all, delete-orphan",
    )

    warehouse_quantities = relationship(
        "QuantityStoredInWarehouse",
        back_populates="build_plan",
        cascade="all, delete-orphan",
    )

    build_request_links = relationship(
        "BuildPlanBuildRequest",
        back_populates="build_plan",
        cascade="all, delete-orphan",
    )

    config_number = relationship(
        "ConfigNumber",
        back_populates="build_plans",
    )

    revisions = relationship(
        "BuildPlanRevision",
        back_populates="build_plan",
        cascade="all, delete-orphan",
        foreign_keys="BuildPlanRevision.build_plan_id",
        order_by=(
            "BuildPlanRevision.work_year, "
            "BuildPlanRevision.work_week, "
            "BuildPlanRevision.file_revision"
        ),
    )

    import_file_touches = relationship(
        "BuildPlanImportFileTouch",
        back_populates="build_plan",
        cascade="all, delete-orphan",
    )

    shippings = relationship(
        "BuildPlanShipping",
        back_populates="build_plan",
        cascade="all, delete-orphan",
    )

    silicon_stepping_links = relationship(
        "BuildPlanSiliconStepping",
        back_populates="build_plan",
        cascade="all, delete-orphan",
    )

    silicon_steppings = relationship(
        "SiliconStepping",
        secondary="build_plan_silicon_steppings",
        viewonly=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "family_form_factor_id",
            "config_number_id",
            name="uq_build_plan_family_form_factor_config_number",
        ),
        Index("ix_build_plans_status", "status"),
        Index("ix_build_plans_family_form_factor_id", "family_form_factor_id"),
        Index("ix_build_plans_config_number_id", "config_number_id"),
        Index("ix_build_plans_ship_date", "ship_date"),
        Index("ix_build_plans_build_start_date", "build_start_date"),
        Index("ix_build_plans_support_activity_id", "support_activity_id"),
    )


# ==========================
# BUILD PLAN ↔ BUILD NOTE
# ==========================

class BuildPlanBuildNote(Base):
    __tablename__ = "build_plan_build_notes"

    id = Column(Integer, primary_key=True)

    build_plan_id = Column(
        Integer,
        ForeignKey("build_plans.id", ondelete="CASCADE"),
        nullable=False,
    )

    build_note_id = Column(
        Integer,
        ForeignKey("build_notes.id", ondelete="CASCADE"),
        nullable=False,
    )

    build_plan = relationship(
        "BuildPlan",
        back_populates="build_note_links",
    )

    build_note = relationship("BuildNote")

    __table_args__ = (
        UniqueConstraint(
            "build_plan_id",
            "build_note_id",
            name="uq_build_plan_build_note",
        ),
    )