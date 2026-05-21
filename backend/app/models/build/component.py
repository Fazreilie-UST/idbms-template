from ..base import Base, Column, Integer, String, relationship, ForeignKey, UniqueConstraint


class Component(Base):
    __tablename__ = "components"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)

    slots = relationship(
        "ComponentSlot",
        back_populates="component",
        cascade="all, delete-orphan",
    )

    suppliers = relationship(
        "Supplier",
        secondary="component_suppliers",
        back_populates="components",
    )


class ComponentSlot(Base):
    __tablename__ = "component_slots"

    id = Column(Integer, primary_key=True, index=True)

    component_id = Column(
        Integer,
        ForeignKey("components.id", ondelete="CASCADE"),
        nullable=False,
    )

    slot_code = Column(String, nullable=False)  # Ch_A, Ch_B, 1, 2

    component = relationship("Component", back_populates="slots")

    __table_args__ = (
        UniqueConstraint(
            "component_id",
            "slot_code",
            name="uq_component_slot",
        ),
    )