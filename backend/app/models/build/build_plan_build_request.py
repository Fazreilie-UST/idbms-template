from ..base import Base, Column, Integer, relationship, ForeignKey, Index


class BuildPlanBuildRequest(Base):
    __tablename__ = "build_plan_build_requests"

    build_plan_id = Column(
        Integer,
        ForeignKey("build_plans.id", ondelete="CASCADE"),
        primary_key=True,
    )

    build_request_id = Column(
        Integer,
        ForeignKey("build_requests.id", ondelete="CASCADE"),
        primary_key=True,
    )

    build_plan = relationship("BuildPlan", back_populates="build_request_links")
    build_request = relationship("BuildRequest", back_populates="build_plan_links")

    __table_args__ = (
        Index("ix_build_plan_build_requests_build_plan_id", "build_plan_id",),
    )