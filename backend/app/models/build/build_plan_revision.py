from ..base import (
    Base,
    Boolean,
    Column,
    Integer,
    DateTime,
    ForeignKey,
    Enum,
    Index,
    JSON,
    UniqueConstraint,
    relationship,
    func,
    text,
)
from .build_plan import BuildPlanStatus


class BuildPlanRevision(Base):
    """Append-only history of changes to a BuildPlan.

    Each import file that introduces a real diff against the previous
    chronological revision creates exactly one BuildPlanRevision. Files that
    contain the same config but no diff are recorded in
    :class:`BuildPlanImportFileTouch` instead.
    """

    __tablename__ = "build_plan_revisions"

    id = Column(Integer, primary_key=True)

    build_plan_id = Column(
        Integer,
        ForeignKey("build_plans.id", ondelete="CASCADE"),
        nullable=False,
    )

    # 1-based, contiguous within a single build_plan_id; resequenced when an
    # out-of-order file is inserted into the middle of history.
    revision_number = Column(Integer, nullable=False)

    # The import file that produced this revision (nullable because seed
    # scripts / manual revisions have no source file). ON DELETE SET NULL so
    # purging an import record never destroys history.
    import_file_id = Column(
        Integer,
        ForeignKey("build_plan_import_files.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Chronological key copied from the source file at the time of import.
    # Kept on the revision row so we can re-sort revisions even after the
    # source file is deleted.
    work_year = Column(Integer, nullable=True)
    work_week = Column(Integer, nullable=True)
    file_revision = Column(Integer, nullable=True)

    # Full snapshot of the build plan + children (components, tests, order
    # requests, warehouse quantities) at the moment this revision was
    # produced. See db/bulk_import_pseudocode.md for the canonical shape.
    snapshot = Column(JSON, nullable=False)

    # Diff vs the previous chronological revision. {} for the very first
    # revision (also marked via the special key __created__).
    changed_fields = Column(JSON, nullable=False, default=dict)

    # Denormalised so the tracker can sort/filter by status without joining
    # back through snapshot JSON.
    status_at_revision = Column(
        Enum(BuildPlanStatus, name="buildplanstatus"),
        nullable=False,
    )

    # True when this revision was produced by an Excel build-plan import
    # file. False for manual revisions authored in the web app. The flag is
    # tightly correlated with ``import_file_id IS NOT NULL`` but is stored
    # explicitly so the UI can show an "Imported" tag without joining back
    # to ``build_plan_import_files``.
    is_imported = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    build_plan = relationship(
        "BuildPlan",
        back_populates="revisions",
        foreign_keys=[build_plan_id],
    )
    import_file = relationship(
        "BuildPlanImportFile",
        foreign_keys=[import_file_id],
    )

    __table_args__ = (
        UniqueConstraint(
            "build_plan_id",
            "revision_number",
            name="uq_build_plan_revision_number",
        ),
        Index(
            "ix_build_plan_revisions_chrono",
            "build_plan_id",
            "work_year",
            "work_week",
            "file_revision",
        ),
    )
