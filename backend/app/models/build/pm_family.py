from ..base import (
    Base,
    Column,
    Integer,
    ForeignKey,
    DateTime,
    UniqueConstraint,
    Index,
    relationship,
    func,
)


class PMFamily(Base):
    """Maps a Program Manager (User) to a Family they are responsible for.

    Used to gate build-plan file uploads: a PM can only upload import files
    whose filename references a family they are assigned to. Admins bypass
    this check.

    Only Admins may create / delete rows in this table.
    """

    __tablename__ = "pm_families"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    family_id = Column(
        Integer,
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user = relationship("User", foreign_keys=[user_id])
    family = relationship("Family", foreign_keys=[family_id])

    __table_args__ = (
        UniqueConstraint("user_id", "family_id", name="uq_pm_family_user_family"),
        Index("ix_pm_families_user_family", "user_id", "family_id"),
    )
