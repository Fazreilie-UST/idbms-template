from ..base import Base, Column, Integer, Numeric, relationship, ForeignKey, BigInteger

class FactFinancialValues(Base):
    __tablename__ = "fact_financial_values"

    stock_id = Column(Integer, ForeignKey("dim_stock.stock_id"), primary_key=True)
    metric_id = Column(BigInteger, ForeignKey("dim_metric.metric_id"), primary_key=True)
    statement_id = Column(Integer, ForeignKey("dim_statement.statement_id"), primary_key=True)
    date_id = Column(Integer, ForeignKey("dim_date.date_id"), primary_key=True)
    value = Column(Numeric(18, 4))

    stock = relationship("DimStock", back_populates="facts")
    metric = relationship("DimMetric", back_populates="facts")
    statement = relationship("DimStatement", back_populates="facts")
    date = relationship("DimDate", back_populates="facts")