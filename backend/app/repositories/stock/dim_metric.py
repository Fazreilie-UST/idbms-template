from sqlalchemy.orm import Session
from app.models.stock.dim_metric import DimMetric

class DimMetricRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, skip: int = 0, limit: int = 100):
        return self.db.query(DimMetric).offset(skip).limit(limit).all()