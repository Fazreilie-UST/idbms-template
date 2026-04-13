from ..base import Base, Column, Integer, Text, relationship, ForeignKey
from sqlalchemy import BigInteger

class DimMetric(Base):
    __tablename__ = "dim_metric"

    metric_id = Column(BigInteger, primary_key=True, index=True)
    metric_name = Column(Text, nullable=False)
    metric_path = Column(Text, nullable=False, unique=True, index=True)
    statement_id = Column(Integer, ForeignKey("dim_statement.statement_id"), nullable=False)
    parent_metric_id = Column(BigInteger, ForeignKey("dim_metric.metric_id"), nullable=True)

    statement = relationship("DimStatement", back_populates="metrics")
    parent = relationship("DimMetric", remote_side=[metric_id], back_populates="children")
    children = relationship("DimMetric", back_populates="parent")
    facts = relationship("FactFinancialValues", back_populates="metric")