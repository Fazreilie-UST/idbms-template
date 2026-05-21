from ..base import Base, Column, Integer, String, relationship


class Forwarder(Base):
    __tablename__ = "forwarders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)

    shippings = relationship("Shipping", back_populates="forwarder")
