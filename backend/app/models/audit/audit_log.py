import enum

from ..base import Base, Column, Integer, String, DateTime, Enum, ForeignKey, JSON, func, Index


class AuditModule(str, enum.Enum):
    user = "User"
    build_plan = "BuildPlan"
    build_request = "BuildRequest"
    shipping = "Shipping"
    component = "Component"
    log_report = "LogReport"


class AuditAction(str, enum.Enum):
    create = "CREATE"
    update = "UPDATE"
    delete = "DELETE"
    status_change = "STATUS_CHANGE"
    assign = "ASSIGN"
    unassign = "UNASSIGN"
    approve = "APPROVE"
    reject = "REJECT"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True)

    # WHO
    user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False
    )

    # WHAT / WHERE
    module = Column(
        Enum(AuditModule), nullable=False
    )
    action = Column(
        Enum(AuditAction), nullable=False
    )

    # WHICH RECORD
    record_id = Column(Integer, nullable=False)

    # CHANGE DETAILS
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)

    # WHEN / WHERE FROM
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    __table_args__ = (
        Index("ix_audit_logs_user_id", "user_id"),
        Index("ix_audit_logs_record_id", "record_id"),
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_module_action", "module", "action"),
    )