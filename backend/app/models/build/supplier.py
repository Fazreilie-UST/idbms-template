from ..base import Base, Column, Integer, String, relationship


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)

    components = relationship(
        "Component",
        secondary="component_suppliers",
        back_populates="suppliers",
    )
    