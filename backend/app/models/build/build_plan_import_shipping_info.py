from ..base import (
    Base,
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
    relationship,
)


class BuildPlanImportShippingInfo(Base):
    """Rows captured from the "Shipping Info" sheet of a build plan import file.

    The sheet lists who is responsible for shipping to a given recipient and
    the recipient's address. The same recipient may appear across many
    different files; rows are scoped to the import file rather than de-duped
    globally so the original document is reproducible.
    """

    __tablename__ = "build_plan_import_shipping_infos"

    id = Column(Integer, primary_key=True, index=True)

    import_file_id = Column(
        Integer,
        ForeignKey("build_plan_import_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Sheet row index (0-based, after collapsing fully-empty rows) for
    # debugging / traceability.
    row_index = Column(Integer, nullable=True)

    responsibility = Column(String(255), nullable=True)
    name = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)

    import_file = relationship(
        "BuildPlanImportFile",
        back_populates="shipping_infos",
        foreign_keys=[import_file_id],
    )

    __table_args__ = (
        UniqueConstraint(
            "import_file_id",
            "responsibility",
            "name",
            "address",
            name="uq_build_plan_import_shipping_info_row",
        ),
        Index(
            "ix_build_plan_import_shipping_infos_file",
            "import_file_id",
        ),
    )
