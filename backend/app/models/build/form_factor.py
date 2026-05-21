from ..base import Base, Column, Integer, String, relationship


class FormFactor(Base):
    """Form Factor reference table.

    Each row represents a canonical form-factor label parsed from a build-plan
    workbook header (e.g. ``"1216 Module"``, ``"1216 Adaptor Module"``,
    ``"2230 Module"``). The importer normalises raw labels into a single
    canonical ``name`` before upserting here; the table is intentionally lean
    — only the name is stored.
    """

    __tablename__ = "form_factors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    details = Column(String, nullable=True)

    family_links = relationship(
        "FamilyFormFactor",
        back_populates="form_factor",
        cascade="all, delete-orphan",
    )
    families = relationship(
        "Family",
        secondary="family_form_factors",
        back_populates="form_factors",
        viewonly=True,
    )
