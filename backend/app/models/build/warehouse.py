from ..base import Base, Column, Integer, String, ForeignKey, relationship


class Warehouse(Base):
    __tablename__ = "warehouses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    notes = Column(String, nullable=True)

    build_plan_quantities = relationship(
        "QuantityStoredInWarehouse",
        back_populates="warehouse",
        cascade="all, delete-orphan",
    )


class QuantityStoredInWarehouse(Base):
    __tablename__ = "quantity_stored_in_warehouse"

    buildplan_id = Column(
        Integer,
        ForeignKey("build_plans.id"),
        primary_key=True,
        nullable=False,
    )

    warehouse_id = Column(
        Integer,
        ForeignKey("warehouses.id"),
        primary_key=True,
        nullable=False,
    )

    quantity_stored = Column(Integer, nullable=False, default=0)

    build_plan = relationship(
        "BuildPlan",
        back_populates="warehouse_quantities",
    )

    warehouse = relationship(
        "Warehouse",
        back_populates="build_plan_quantities",
    )