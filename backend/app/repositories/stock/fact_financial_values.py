from sqlalchemy.orm import Session
from app.models.stock.fact_financial_values import FactFinancialValues

class FactFinancialValuesRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, skip: int = 0, limit: int = 100):
        return self.db.query(FactFinancialValues).offset(skip).limit(limit).all()