from ..base import (
    Base,
    Column,
    Integer,
    String,
    ForeignKey,
    relationship,
    UniqueConstraint,
    Index,
)


class ComponentAttributeValue(Base):
    __tablename__ = "component_attribute_values"

    id = Column(Integer, primary_key=True, index=True)

    build_plan_component_id = Column(
        Integer,
        ForeignKey("build_plan_components.id", ondelete="CASCADE"),
        nullable=False,
    )

    attribute_id = Column(
        Integer,
        ForeignKey("attribute_definitions.id"),
        nullable=False,
    )

    value_text = Column(String, nullable=True)
    value_number = Column(Integer, nullable=True)

    build_plan_component = relationship(
        "BuildPlanComponent",
        back_populates="attribute_values",
    )

    attribute = relationship("AttributeDefinition")

    __table_args__ = (
        UniqueConstraint(
            "build_plan_component_id",
            "attribute_id",
            name="uq_build_plan_component_attribute",
        ),
        Index(
            "ix_component_attribute_values_bpc_id",
            "build_plan_component_id",
        ),

        Index(
            "ix_component_attribute_values_attribute_id",
            "attribute_id",
        ),
    )