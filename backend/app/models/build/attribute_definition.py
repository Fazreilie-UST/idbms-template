from ..base import Base, Column, Integer, String


class AttributeDefinition(Base):
    __tablename__ = "attribute_definitions"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    data_type = Column(String, nullable=False, default="text")