from ..base import (
    Base,
    Column,
    Integer,
    ForeignKey,
    UniqueConstraint,
    Index,
    relationship,
)


class BuildPlanShipping(Base):
    """Per-build-plan recipient -> requestor membership.

    Encodes the nested shape "for build plan X, recipient (user) R groups
    these requestor users together with their quantities". One row per
    (recipient_user, requestor_user) pair within a single build plan; the
    recipient user is the "handler" for the SUM-formula format or the
    bold/group-header row for the legacy "Others" format.
    """

    __tablename__ = "build_plan_shippings"

    id = Column(Integer, primary_key=True, index=True)

    build_plan_id = Column(
        Integer,
        ForeignKey("build_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    recipient_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    requestor_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    quantity = Column(Integer, nullable=True)

    build_plan = relationship("BuildPlan", back_populates="shippings")
    recipient_user = relationship("User", foreign_keys=[recipient_user_id])
    requestor_user = relationship("User", foreign_keys=[requestor_user_id])

    __table_args__ = (
        UniqueConstraint(
            "build_plan_id",
            "recipient_user_id",
            "requestor_user_id",
            name="uq_build_plan_shipping_recipient_requestor",
        ),
        Index(
            "ix_build_plan_shippings_plan_recipient",
            "build_plan_id",
            "recipient_user_id",
        ),
    )
