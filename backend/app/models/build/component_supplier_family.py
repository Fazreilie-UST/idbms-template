from sqlalchemy import ForeignKeyConstraint

from ..base import Base, Column, Integer, ForeignKey, Index


class ComponentSupplierFamily(Base):
    """Three-way junction: which families a (component, supplier) pair supplies.

    The (component_id, supplier_id) pair must already exist in
    ``component_suppliers``; this table refines that relationship by
    enumerating the families the supplier provides the component for.
    """

    __tablename__ = "component_supplier_families"

    component_id = Column(Integer, primary_key=True, nullable=False)
    supplier_id = Column(Integer, primary_key=True, nullable=False)
    family_id = Column(
        Integer,
        ForeignKey("families.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["component_id", "supplier_id"],
            ["component_suppliers.component_id", "component_suppliers.supplier_id"],
            ondelete="CASCADE",
        ),
        Index("ix_csf_family", "family_id"),
        Index("ix_csf_component_supplier", "component_id", "supplier_id"),
    )
