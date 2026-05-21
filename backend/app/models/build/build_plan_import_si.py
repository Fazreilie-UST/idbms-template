from ..base import (
    Base,
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    Index,
    relationship,
)


class BuildPlanImportSi(Base):
    """Rows captured from the "Si" sheet of a build plan import file.

    Each row tracks a Si lot's request / commit / actual quantities and dock
    work-weeks. Stored verbatim against the import file; duplicates are
    permitted because the same lot may legitimately appear in multiple files
    (or even multiple times in the same file with different states).

    Dock date columns are kept as free-form strings — the source file uses
    work-week notation (e.g. ``WW16'26``) rather than calendar dates, and we
    want to round-trip whatever the spreadsheet contained.
    """

    __tablename__ = "build_plan_import_si_rows"

    id = Column(Integer, primary_key=True, index=True)

    import_file_id = Column(
        Integer,
        ForeignKey("build_plan_import_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 0-based row index within the Si sheet (after the header row).
    row_index = Column(Integer, nullable=True)

    si_description = Column(String(500), nullable=True)
    si_lot_numbers = Column(String(500), nullable=True)
    class_test_rev = Column(String(255), nullable=True)

    request_qty = Column(Integer, nullable=True)
    request_dock_date = Column(String(64), nullable=True)

    commit_qty = Column(Integer, nullable=True)
    commit_dock_date = Column(String(64), nullable=True)

    actual_qty = Column(Integer, nullable=True)
    actual_dock_date = Column(String(64), nullable=True)

    comments = Column(Text, nullable=True)

    import_file = relationship(
        "BuildPlanImportFile",
        back_populates="si_rows",
        foreign_keys=[import_file_id],
    )

    __table_args__ = (
        Index(
            "ix_build_plan_import_si_rows_file",
            "import_file_id",
        ),
    )
