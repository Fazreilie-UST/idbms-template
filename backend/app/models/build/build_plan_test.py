from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship

from app.db.base import Base


class BuildPlanTest(Base):
    __tablename__ = "build_plan_tests"

    id = Column(Integer, primary_key=True, index=True)

    build_plan_id = Column(
        Integer,
        ForeignKey("build_plans.id", ondelete="CASCADE"),
        nullable=False,
    )

    test_id = Column(
        Integer,
        ForeignKey("tests.id", ondelete="CASCADE"),
        nullable=False,
    )

    test_detail_id = Column(
        Integer,
        ForeignKey("test_details.id", ondelete="SET NULL"),
        nullable=True,
    )

    build_plan = relationship("BuildPlan", back_populates="tests")
    test = relationship("Test", back_populates="build_plan_tests")
    test_detail = relationship("TestDetail", back_populates="build_plan_tests")

    __table_args__ = (
        UniqueConstraint(
            "build_plan_id",
            "test_id",
            "test_detail_id",
            name="uq_build_plan_test_detail",
        ),
        Index("ix_build_plan_tests_build_plan_id", "build_plan_id"),
        Index("ix_build_plan_tests_test_id", "test_id"),
    )