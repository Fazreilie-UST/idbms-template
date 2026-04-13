from sqlalchemy.orm import Session
from app.models.stock.import_job import ImportJob

class DimImportJobRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, skip: int = 0, limit: int = 100):
        return self.db.query(ImportJob).offset(skip).limit(limit).all()