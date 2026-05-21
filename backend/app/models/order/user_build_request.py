from ..base import Base, Column, Integer, ForeignKey


class UserBuildRequest(Base):
    __tablename__ = "user_build_requests"

    requestor_id = Column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        primary_key=True
    )

    build_request_id = Column(
        Integer, 
        ForeignKey("build_requests.id", ondelete="CASCADE"),
        primary_key=True
    ) 