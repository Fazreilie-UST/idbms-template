from ..base import (
    Base,
    Column,
    Integer,
    String,
    relationship,
)


class ConfigNumber(Base):
    __tablename__ = "config_numbers"

    id = Column(Integer, primary_key=True)

    value = Column(String, nullable=False, unique=True, index=True)

    build_plans = relationship(
        "BuildPlan",
        back_populates="config_number",
    )

    build_requests = relationship(
        "BuildRequest",
        back_populates="config_number",
    )

    shippings = relationship(
        "Shipping",
        back_populates="config_number",
    )
