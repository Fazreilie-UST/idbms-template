from ..base import Base, Column, Integer, ForeignKey, Boolean, relationship, UniqueConstraint, Index


class BuildPlanComponent(Base):
    __tablename__ = "build_plan_components"

    id = Column(Integer, primary_key=True, index=True)

    build_plan_id = Column(
        Integer,
        ForeignKey("build_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    component_id = Column(
        Integer,
        ForeignKey("components.id"),
        nullable=False,
        index=True,
    )

    slot_id = Column(
        Integer,
        ForeignKey("component_slots.id"),
        nullable=True,
    )

    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id"),
        nullable=True,
    )

    is_key = Column(Boolean, default=False)

    build_plan = relationship("BuildPlan", back_populates="components")
    component = relationship("Component")
    slot = relationship("ComponentSlot")
    supplier = relationship("Supplier")

    attribute_values = relationship(
        "ComponentAttributeValue",
        back_populates="build_plan_component",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "build_plan_id",
            "component_id",
            "slot_id",
            name="uq_plan_component_slot",
        ),

        Index(
            "ix_build_plan_components_build_plan_id",
            "build_plan_id",
        ),

        Index(
            "ix_build_plan_components_component_id",
            "component_id",
        ),
    )