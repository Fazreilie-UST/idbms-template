from ..base import Base, Column, Integer, String,relationship

class ActionCategory(Base):
    __tablename__ = "action_categories"

    id = Column(Integer, nullable=False, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)

    permissions = relationship("Permission", back_populates="action_category")


"""
create
read
update
delete
approve
send
lock
revise
manage
"""