from ..base import Base, Column, Integer, ForeignKey


class ComponentSupplier(Base):
    __tablename__ = "component_suppliers"

    component_id = Column(
        Integer,
        ForeignKey("components.id", ondelete="CASCADE"),
        primary_key=True,
    )

    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        primary_key=True,
    )