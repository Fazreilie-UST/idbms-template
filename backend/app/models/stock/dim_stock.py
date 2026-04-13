from ..base import Base, Column, Integer, Text, Numeric, relationship

class DimStock(Base):
    __tablename__ = "dim_stock"

    stock_id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(Text, nullable=False, unique=True)
    stock_number = Column(Text, nullable=False, unique=True)
    stock_name = Column(Text,  nullable=False)
    weblink = Column(Text, nullable=True)
    price = Column(Numeric(18, 4))

    facts = relationship("FactFinancialValues", back_populates="stock")