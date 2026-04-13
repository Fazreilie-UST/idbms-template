from sqlalchemy import create_engine, Column, Integer, String, Date, Numeric, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from pydantic import BaseModel
from typing import Optional, List

# SQLAlchemy setup
DATABASE_URL = "postgresql://user:password@localhost/dbname"  # Replace with your actual DB URL
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# SQLAlchemy Models
class DimStatement(Base):
    __tablename__ = "dim_statement"

    statement_id = Column(Integer, primary_key=True, index=True)
    statement_name = Column(Text, nullable=False)

    metrics = relationship("DimMetric", back_populates="statement")
    facts = relationship("FactFinancialValues", back_populates="statement")

class DimDate(Base):
    __tablename__ = "dim_date"

    date_id = Column(Integer, primary_key=True, index=True)
    full_date = Column(Date, nullable=False)
    year = Column(Integer)
    month = Column(Integer)
    quarter = Column(Integer)

    facts = relationship("FactFinancialValues", back_populates="date")

class DimStock(Base):
    __tablename__ = "dim_stock"

    stock_id = Column(Integer, primary_key=True, index=True)
    stock_code = Column(Text, nullable=False)
    stock_number = Column(Integer)
    stock_name = Column(Text)
    weblink = Column(Text)
    price = Column(Numeric(18, 4))

    facts = relationship("FactFinancialValues", back_populates="stock")

class DimMetric(Base):
    __tablename__ = "dim_metric"

    metric_id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(Text, nullable=False)
    statement_id = Column(Integer, ForeignKey("dim_statement.statement_id"), nullable=False)
    parent_metric_id = Column(Integer, ForeignKey("dim_metric.metric_id"))

    statement = relationship("DimStatement", back_populates="metrics")
    parent = relationship("DimMetric", remote_side=[metric_id])
    children = relationship("DimMetric", back_populates="parent")
    facts = relationship("FactFinancialValues", back_populates="metric")

class FactFinancialValues(Base):
    __tablename__ = "fact_financial_values"

    stock_id = Column(Integer, ForeignKey("dim_stock.stock_id"), primary_key=True)
    metric_id = Column(Integer, ForeignKey("dim_metric.metric_id"), primary_key=True)
    statement_id = Column(Integer, ForeignKey("dim_statement.statement_id"), primary_key=True)
    date_id = Column(Integer, ForeignKey("dim_date.date_id"), primary_key=True)
    value = Column(Numeric(18, 4))

    stock = relationship("DimStock", back_populates="facts")
    metric = relationship("DimMetric", back_populates="facts")
    statement = relationship("DimStatement", back_populates="facts")
    date = relationship("DimDate", back_populates="facts")

# Pydantic Schemas
class DimStatementBase(BaseModel):
    statement_name: str

class DimStatementCreate(DimStatementBase):
    pass

class DimStatement(DimStatementBase):
    statement_id: int

    class Config:
        from_attributes = True

class DimDateBase(BaseModel):
    full_date: str  # ISO format date
    year: Optional[int]
    month: Optional[int]
    quarter: Optional[int]

class DimDateCreate(DimDateBase):
    pass

class DimDate(DimDateBase):
    date_id: int

    class Config:
        from_attributes = True

class DimStockBase(BaseModel):
    stock_code: str
    stock_number: Optional[int]
    stock_name: Optional[str]
    weblink: Optional[str]
    price: Optional[float]

class DimStockCreate(DimStockBase):
    pass

class DimStock(DimStockBase):
    stock_id: int

    class Config:
        from_attributes = True

class DimMetricBase(BaseModel):
    metric_name: str
    statement_id: int
    parent_metric_id: Optional[int]

class DimMetricCreate(DimMetricBase):
    pass

class DimMetric(DimMetricBase):
    metric_id: int

    class Config:
        from_attributes = True

class FactFinancialValuesBase(BaseModel):
    stock_id: int
    metric_id: int
    statement_id: int
    date_id: int
    value: Optional[float]

class FactFinancialValuesCreate(FactFinancialValuesBase):
    pass

class FactFinancialValues(FactFinancialValuesBase):
    class Config:
        from_attributes = True

# Alembic setup notes:
# To set up Alembic:
# 1. Install alembic: pip install alembic
# 2. Initialize alembic: alembic init alembic
# 3. Edit alembic.ini to set sqlalchemy.url
# 4. Edit alembic/env.py to import your models and set target_metadata = Base.metadata
# 5. Run alembic revision --autogenerate -m "Initial migration"
# 6. Run alembic upgrade head