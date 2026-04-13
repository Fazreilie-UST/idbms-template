from app.models.stock.dim_stock import DimStock
from app.models.stock.dim_date import DimDate
from app.models.stock.dim_statement import DimStatement
from app.models.stock.dim_metric import DimMetric
from app.models.stock.fact_financial_values import FactFinancialValues


class StockService:
    def __init__(self, db):
        self.db = db

    def _paginate_query(self, query, skip: int = 0, limit: int = 100):
        total = query.count()
        items = query.offset(skip).limit(limit).all()

        return {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    def _apply_sorting(self, query, allowed_sort_columns: dict, sort_by: str | None, sort_order: str = "asc", default_sort=None):
        sort_column = allowed_sort_columns.get(sort_by, default_sort)

        if sort_column is None:
            return query

        if str(sort_order).lower() == "desc":
            return query.order_by(sort_column.desc())

        return query.order_by(sort_column.asc())

    def get_stock_master(
        self,
        skip: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ):
        query = self.db.query(DimStock)

        allowed_sort_columns = {
            "stock_id": DimStock.stock_id,
            "stock_code": DimStock.stock_code,
            "stock_number": DimStock.stock_number,
            "stock_name": DimStock.stock_name,
            "price": DimStock.price,
        }

        query = self._apply_sorting(
            query=query,
            allowed_sort_columns=allowed_sort_columns,
            sort_by=sort_by,
            sort_order=sort_order,
            default_sort=DimStock.stock_id,
        )

        return self._paginate_query(query, skip=skip, limit=limit)

    def get_dates(self, skip: int = 0, limit: int = 100):
        query = self.db.query(DimDate).order_by(DimDate.date_id.asc())
        return self._paginate_query(query, skip=skip, limit=limit)

    def get_statements(self, skip: int = 0, limit: int = 100):
        query = self.db.query(DimStatement).order_by(DimStatement.statement_id.asc())
        return self._paginate_query(query, skip=skip, limit=limit)

    def get_metrics(self, skip: int = 0, limit: int = 100):
        query = self.db.query(DimMetric).order_by(DimMetric.metric_id.asc())
        return self._paginate_query(query, skip=skip, limit=limit)

    def get_facts(
        self,
        skip: int = 0,
        limit: int = 100,
        sort_by: str | None = None,
        sort_order: str = "asc",
    ):
        query = self.db.query(FactFinancialValues)

        allowed_sort_columns = {
            "stock_id": FactFinancialValues.stock_id,
            "metric_id": FactFinancialValues.metric_id,
            "statement_id": FactFinancialValues.statement_id,
            "date_id": FactFinancialValues.date_id,
        }

        query = self._apply_sorting(
            query=query,
            allowed_sort_columns=allowed_sort_columns,
            sort_by=sort_by,
            sort_order=sort_order,
            default_sort=FactFinancialValues.stock_id,
        )

        return self._paginate_query(query, skip=skip, limit=limit)