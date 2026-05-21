"""Silicon stepping reference + per-build-plan link table.

The "Silicon Stepping" cell of a build plan workbook may contain multiple
whitespace-separated tokens. Each entry is a *base* stepping (one of the
five canonical names: ``STC``, ``A0``, ``A1``, ``B0``, ``B1``) optionally
followed by one or more **suffix** tokens that qualify it (e.g.
``"A1 FLV1"`` or ``"A0 FFFF"``).

The reference table :class:`SiliconStepping` stores ONLY the five canonical
base names (deduped). Per-build-plan occurrences (with optional suffix) are
stored as rows in :class:`BuildPlanSiliconStepping`. A build plan can carry
multiple base steppings, each possibly with a different suffix.
"""

from ..base import (
    Base,
    Column,
    Integer,
    String,
    ForeignKey,
    UniqueConstraint,
    relationship,
)


# Canonical base silicon steppings recognised by the importer.
# Any token NOT in this set is treated as a suffix to the most recent base.
BASE_SILICON_STEPPINGS: tuple[str, ...] = ("STC", "A0", "A1", "B0", "B1")


class SiliconStepping(Base):
    __tablename__ = "silicon_steppings"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True, index=True)


class BuildPlanSiliconStepping(Base):
    __tablename__ = "build_plan_silicon_steppings"

    id = Column(Integer, primary_key=True)

    build_plan_id = Column(
        Integer,
        ForeignKey("build_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    silicon_stepping_id = Column(
        Integer,
        ForeignKey("silicon_steppings.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Optional qualifier captured after the base stepping (e.g. ``"FLV1"``,
    # ``"FFFF"``). NULL means the workbook listed the base stepping alone.
    suffix = Column(String, nullable=True)

    build_plan = relationship(
        "BuildPlan",
        back_populates="silicon_stepping_links",
    )
    silicon_stepping = relationship("SiliconStepping")

    __table_args__ = (
        UniqueConstraint(
            "build_plan_id",
            "silicon_stepping_id",
            "suffix",
            name="uq_build_plan_silicon_stepping_suffix",
        ),
    )
