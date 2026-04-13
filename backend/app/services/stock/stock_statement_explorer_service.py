from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.stock.fact_financial_values import FactFinancialValues
from app.models.stock.dim_stock import DimStock
from app.models.stock.dim_metric import DimMetric
from app.models.stock.dim_statement import DimStatement
from app.models.stock.dim_date import DimDate


class StockStatementExplorerService:
    def __init__(self, db: Session):
        self.db = db

    def preview(self, payload):
        stock = (
            self.db.query(DimStock)
            .filter(DimStock.stock_id == payload.stock_id)
            .first()
        )

        statement = (
            self.db.query(DimStatement)
            .filter(DimStatement.statement_id == payload.statement_id)
            .first()
        )

        base_query = (
            self.db.query(
                FactFinancialValues.metric_id.label("metric_id"),
                DimMetric.metric_name.label("metric_name"),
                DimMetric.parent_metric_id.label("parent_metric_id"),
                DimDate.year.label("year"),
                DimDate.month.label("month"),
                FactFinancialValues.value.label("value"),
            )
            .join(DimMetric, FactFinancialValues.metric_id == DimMetric.metric_id)
            .join(DimDate, FactFinancialValues.date_id == DimDate.date_id)
            .filter(FactFinancialValues.stock_id == payload.stock_id)
            .filter(FactFinancialValues.statement_id == payload.statement_id)
            .order_by(DimMetric.metric_name.asc(), DimDate.year.asc(), DimDate.month.asc())
        )

        raw_rows = base_query.all()

        rows = [
            {
                "metric_id": row.metric_id,
                "metric_name": row.metric_name,
                "parent_metric_id": row.parent_metric_id,
                "date": self._build_date_label(row.year, row.month),
                "value": float(row.value) if row.value is not None else None,
            }
            for row in raw_rows
        ]

        total_metrics = (
            self.db.query(func.count(func.distinct(FactFinancialValues.metric_id)))
            .filter(FactFinancialValues.stock_id == payload.stock_id)
            .filter(FactFinancialValues.statement_id == payload.statement_id)
            .scalar()
        ) or 0

        total_dates = (
            self.db.query(func.count(func.distinct(FactFinancialValues.date_id)))
            .filter(FactFinancialValues.stock_id == payload.stock_id)
            .filter(FactFinancialValues.statement_id == payload.statement_id)
            .scalar()
        ) or 0

        return {
            "summary": {
                "stock_id": payload.stock_id,
                "stock_code": stock.stock_code if stock else None,
                "stock_name": stock.stock_name if stock else None,
                "statement_id": payload.statement_id,
                "statement_name": statement.statement_name if statement else None,
                "total_rows": len(rows),
                "total_metrics": total_metrics,
                "total_dates": total_dates,
            },
            "rows": rows,
        }

    @staticmethod
    def _build_date_label(year, month):
        if year is None:
            return None

        if month is None:
            return str(year)

        return f"{year}-{str(month).zfill(2)}"