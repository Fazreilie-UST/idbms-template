from ..base import Base, Column, Integer, ForeignKey, relationship


class FamilyFormFactor(Base):
    __tablename__ = "family_form_factors"

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(
        Integer,
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
    )
    form_factor_id = Column(
        Integer,
        ForeignKey("form_factors.id", ondelete="CASCADE"),
        nullable=False,
    )

    family = relationship("Family", back_populates="family_form_factors")
    form_factor = relationship("FormFactor", back_populates="family_links")
    accesses = relationship(
        "BuildPlanAccess",
        back_populates="family_form_factor",
        cascade="all, delete-orphan",
    )
