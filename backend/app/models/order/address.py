from ..base import (
    Base,
    Column,
    Integer,
    String,
    Text,
    Boolean,
    ForeignKey,
    relationship,
)


class Address(Base):
    """Reusable shipping address.

    An Address can be attached to a user (preferred personal address) or
    to neither (free-floating, referenced only by a specific shipment).
    """

    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)

    label = Column(String, nullable=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    line1 = Column(String, nullable=True)
    line2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)

    notes = Column(Text, nullable=True)

    is_default = Column(Boolean, nullable=False, default=False)

    user = relationship("User", foreign_keys=[user_id])
