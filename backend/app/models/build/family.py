from ..base import Base, Column, Integer, String, relationship

class Family(Base):
    __tablename__ = "families"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=False, unique=True) 
    description = Column(String, nullable= True)

    family_form_factors = relationship(
        "FamilyFormFactor",
        back_populates="family",
        cascade="all, delete-orphan",
    )
    form_factors = relationship(
        "FormFactor",
        secondary="family_form_factors",
        back_populates="families",
        viewonly=True,
    )