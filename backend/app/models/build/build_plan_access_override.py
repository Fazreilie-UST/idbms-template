from ..base import Base, Column, Integer, Enum, ForeignKey, relationship, UniqueConstraint
from .build_plan_access import AccessTypeEnum


class BuildPlanAccessOverride(Base):
    """Per-build-plan access override.

    Coexists with :class:`BuildPlanAccess` (family/FormFactor-level access). A user's
    effective access on a build plan is the *maximum* of:
      * the family/FormFactor-level row (if any), and
      * the plan-level override row (if any).

    Overrides can only **raise** access, never lower it. The query helpers in
    the service layer enforce this when computing "managed by me" filters.

    Rationale: a PM usually handles an entire product family (modeled as
    ``BuildPlanAccess`` on the family-FormFactor). Occasionally a different PM needs
    to step in on a single build plan / config number; in that case we store
    one tiny override row here rather than granting them blanket family-wide
    access.
    """

    __tablename__ = "build_plan_access_overrides"

    id = Column(Integer, primary_key=True, index=True)
    build_plan_id = Column(
        Integer,
        ForeignKey("build_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    access_type = Column(
        Enum(AccessTypeEnum, name="build_plan_access_type"),
        nullable=False,
        default=AccessTypeEnum.editor,
    )

    build_plan = relationship("BuildPlan")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "build_plan_id",
            "user_id",
            name="uq_bp_access_override_plan_user",
        ),
    )
