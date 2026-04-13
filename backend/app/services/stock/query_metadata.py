from sqlalchemy import func

from app.models.stock.dim_stock import DimStock
from app.models.stock.dim_date import DimDate
from app.models.stock.dim_metric import DimMetric
from app.models.stock.dim_statement import DimStatement
from app.models.stock.fact_financial_values import FactFinancialValues

ALLOWED_TABLES = {
    "dim_stock": DimStock,
    "dim_date": DimDate,
    "dim_metric": DimMetric,
    "dim_statement": DimStatement,
    "fact_financial_values": FactFinancialValues,
}

ALLOWED_COLUMNS = {
    "dim_stock": {"stock_id", "stock_code", "stock_number", "stock_name", "weblink", "price"},
    "dim_date": {"date_id", "full_date", "year", "month"},
    "dim_metric": {"metric_id", "metric_name", "statement_id", "parent_metric_id"},
    "dim_statement": {"statement_id", "statement_name"},
    "fact_financial_values": {"stock_id", "metric_id", "statement_id", "date_id", "value"},
}

JOIN_MAP = {
    "dim_stock": (
        DimStock,
        FactFinancialValues.stock_id == DimStock.stock_id,
    ),
    "dim_metric": (
        DimMetric,
        FactFinancialValues.metric_id == DimMetric.metric_id,
    ),
    "dim_statement": (
        DimStatement,
        FactFinancialValues.statement_id == DimStatement.statement_id,
    ),
    "dim_date": (
        DimDate,
        FactFinancialValues.date_id == DimDate.date_id,
    ),
}

AGGREGATION_MAP = {
    "sum": func.sum,
    "avg": func.avg,
    "min": func.min,
    "max": func.max,
    "count": func.count,
}