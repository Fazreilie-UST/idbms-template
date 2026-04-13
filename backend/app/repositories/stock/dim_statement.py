from sqlalchemy.orm import Session
from app.models.stock.dim_statement import DimStatement

class DimStatementRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, skip: int = 0, limit: int = 100):
        return self.db.query(DimStatement).offset(skip).limit(limit).all()