from ..base import Base, Column, Integer, Text, Numeric, relationship

class DimStatement(Base):
    __tablename__ = "dim_statement"

    statement_id = Column(Integer, primary_key=True, index=True)
    statement_name = Column(Text, nullable=False, unique=True)

    metrics = relationship("DimMetric", back_populates="statement")
    facts = relationship("FactFinancialValues", back_populates="statement")