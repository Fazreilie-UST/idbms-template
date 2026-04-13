from sqlalchemy.orm import Session
from app.models.stock.dim_stock import DimStock


class DimStockRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, skip: int = 0, limit: int = 100):
        return self.db.query(DimStock).offset(skip).limit(limit).all()