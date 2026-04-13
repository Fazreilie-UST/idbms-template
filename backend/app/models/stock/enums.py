from enum import Enum


class ImportExportTableName(str, Enum):
    DIM_METRIC = "dim_metric"
    DIM_STOCK = "dim_stock"
    DIM_STATEMENT = "dim_statement"
    DIM_DATE = "dim_date"
    FACT_FINANCIAL_VALUES = "fact_financial_values"


class FileType(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"