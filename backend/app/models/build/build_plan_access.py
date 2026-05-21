import enum

from ..base import Base, Column, Integer, Enum, ForeignKey, relationship, UniqueConstraint


class AccessTypeEnum(str, enum.Enum):
    owner = "owner"
    editor = "editor"
    # viewer is implicit and therefore not stored in this table.


class BuildPlanAccess(Base):
    __tablename__ = "build_plan_access"

    access_id = Column(Integer, primary_key=True, index=True)
    family_form_factor_id = Column(Integer, ForeignKey("family_form_factors.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    access_type = Column(
        Enum(AccessTypeEnum, name="build_plan_access_type"),
        nullable=False,
        default=AccessTypeEnum.editor,
    )

    family_form_factor = relationship("FamilyFormFactor", back_populates="accesses")
    user = relationship("User")

    __table_args__ = (
        UniqueConstraint(
            "family_form_factor_id",
            "user_id",
            name="uq_build_plan_access_family_form_factor_user",
        ),
    )


"""
Access rules:
    - viewer (implicit, all authenticated users — no row stored)
    - editor (explicit row, granted by owner)
    - owner (explicit row, the PM who handles the program)

Rows are only stored for editor and owner access.
Absence of a row means the user has the default viewer access.
"""

