from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base import Base


class Test(Base):
    __tablename__ = "tests"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    details = relationship(
        "TestDetail",
        back_populates="test",
        cascade="all, delete-orphan",
    )

    build_plan_tests = relationship(
        "BuildPlanTest",
        back_populates="test",
        cascade="all, delete-orphan",
    )


class TestDetail(Base):
    __tablename__ = "test_details"

    id = Column(Integer, primary_key=True, index=True)

    test_id = Column(
        Integer,
        ForeignKey("tests.id", ondelete="CASCADE"),
        nullable=False,
    )

    detail = Column(String(255), nullable=False)

    test = relationship("Test", back_populates="details")

    build_plan_tests = relationship(
        "BuildPlanTest",
        back_populates="test_detail",
    )

    __table_args__ = (
        UniqueConstraint("test_id", "detail", name="uq_test_detail"),
    )