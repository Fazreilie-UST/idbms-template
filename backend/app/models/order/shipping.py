import enum

from ..base import Base, Column, Integer, Date, String, Text, Enum, relationship, ForeignKey


class ShippingStatus(str, enum.Enum):
    scheduled = "Scheduled"
    shipped_out = "ShippedOut"
    delivered = "Delivered"
    completed = "Completed" # auto set after 14 days OR users verified shipment


class Shipping(Base):
    __tablename__ = "shippings"

    id = Column(Integer, primary_key=True, index=True)

    config_number_id = Column(
        Integer,
        ForeignKey("config_numbers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # The package recipient (a.k.a. "Handler" on the Shipments tab):
    # the single user the box physically ships to. Downstream "Recipients"
    # of the parts within that box are derived from BuildRequests linked
    # via ``build_plan_shippings``.
    recipient_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    tracking_number = Column(String, nullable=True)
    forwarder_id = Column(
        Integer,
        ForeignKey("forwarders.id", ondelete="SET NULL"),
        nullable=True,
    )
    quantity = Column(Integer, nullable=True)
    comments = Column(Text, nullable=True)

    ship_date = Column(Date, nullable=True)
    eta = Column(Date, nullable=True)
    delivery_date = Column(Date, nullable=True)

    status = Column(
        Enum(ShippingStatus, name="shipping_status"),
        nullable=False,
        default=ShippingStatus.scheduled,
        index=True,
    )

    config_number = relationship("ConfigNumber", back_populates="shippings")
    recipient_user = relationship("User", foreign_keys=[recipient_user_id])
    forwarder = relationship("Forwarder", back_populates="shippings")