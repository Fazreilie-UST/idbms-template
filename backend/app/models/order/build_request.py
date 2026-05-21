import enum

from ..base import Base, Column, Integer, Enum, relationship, ForeignKey


class BuildRequestStatus(str, enum.Enum):
    draft = "Draft"
    submitted = "Submitted"
    underReview = "Under Review"
    cancelled = "Cancelled"
    rejected = "Rejected"
    approved = "Approved"
    planned = "Planned"
    locked = "Locked"
    completed = "Completed"
    none = "None"


class BuildRequest(Base):
    __tablename__ = "build_requests"

    id = Column(Integer, primary_key=True)

    requestor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    family_form_factor_id = Column(Integer, ForeignKey("family_form_factors.id"), nullable=False, index=True)

    config_number_id = Column(
        Integer,
        ForeignKey("config_numbers.id"),
        nullable=False,
        index=True,
    )

    quantity = Column(Integer, nullable=False)
    status = Column(Enum(BuildRequestStatus), nullable=False, index=True)

    revision = Column(Integer, nullable=False, default=1)

    previous_build_request_id = Column(
        Integer,
        ForeignKey("build_requests.id"),
        nullable=True,
    )

    previous_build_request = relationship(
        "BuildRequest",
        remote_side=[id],
    )

    build_plan_links = relationship(
        "BuildPlanBuildRequest",
        back_populates="build_request",
        cascade="all, delete-orphan",
    )

    config_number = relationship(
        "ConfigNumber",
        back_populates="build_requests",
    )

    # Read-only relationship to the requesting user. Defined here (rather
    # than back-populated from User) to keep User unaware of order semantics.
    requestor = relationship(
        "User",
        foreign_keys=[requestor_id],
        lazy="joined",
        viewonly=True,
    )