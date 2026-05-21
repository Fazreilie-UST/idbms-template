from ..base import (
    Base,
    Column,
    Integer,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    relationship,
    func,
)


class BuildPlanImportFileTouch(Base):
    """Records that an import file was processed against a BuildPlan but the
    file's contents matched an existing revision (no diff). Lets us answer
    "was this file ever processed for this config?" without inflating the
    revision history.
    """

    __tablename__ = "build_plan_import_file_touches"

    id = Column(Integer, primary_key=True)

    import_file_id = Column(
        Integer,
        ForeignKey("build_plan_import_files.id", ondelete="CASCADE"),
        nullable=False,
    )

    build_plan_id = Column(
        Integer,
        ForeignKey("build_plans.id", ondelete="CASCADE"),
        nullable=False,
    )

    matched_revision_id = Column(
        Integer,
        ForeignKey("build_plan_revisions.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    import_file = relationship(
        "BuildPlanImportFile",
        foreign_keys=[import_file_id],
    )
    build_plan = relationship(
        "BuildPlan",
        back_populates="import_file_touches",
        foreign_keys=[build_plan_id],
    )
    matched_revision = relationship(
        "BuildPlanRevision",
        foreign_keys=[matched_revision_id],
    )

    __table_args__ = (
        UniqueConstraint(
            "import_file_id",
            "build_plan_id",
            name="uq_import_file_touch_file_plan",
        ),
    )
