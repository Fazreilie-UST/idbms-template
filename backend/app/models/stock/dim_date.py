from ..base import Base, Column, Integer, Date, relationship

class DimDate(Base):
    __tablename__ = "dim_date"

    date_id = Column(Integer, primary_key=True, index=True)
    full_date = Column(Date, nullable=False, unique=True)
    year = Column(Integer)
    month = Column(Integer)

    facts = relationship("FactFinancialValues", back_populates="date")