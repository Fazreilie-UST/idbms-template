import json
import csv
from pathlib import Path
from datetime import datetime


BASE_DIR = Path("stock")
INPUT_DIR = BASE_DIR / "original_data"
OUTPUT_DIR = BASE_DIR / "transformed_data" / "b1"

FINANCIAL_JSON = INPUT_DIR / "financial1.json"
STOCK_MASTER_CSV = INPUT_DIR / "stock_master.csv"

DIM_STOCK_CSV = OUTPUT_DIR / "dim_stock.csv"
DIM_STATEMENT_CSV = OUTPUT_DIR / "dim_statement.csv"
DIM_METRIC_CSV = OUTPUT_DIR / "dim_metric.csv"
DIM_DATE_CSV = OUTPUT_DIR / "dim_date.csv"
FACT_CSV = OUTPUT_DIR / "fact_financial_values.csv"


def clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_stock_number(value):
    value = clean_text(value)
    if not value:
        return ""
    return value.zfill(4)


def load_json(filepath: Path):
    with filepath.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_stock_master(filepath: Path):
    stock_master = {}

    with filepath.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            stock_code = clean_text(row.get("STOCK CODE"))
            stock_number = normalize_stock_number(row.get("STOCK NUMBER"))

            # Skip rows with no stock_number because it is our business key
            if not stock_number:
                continue

            stock_master[stock_code] = {
                "stock_code": stock_code,
                "stock_number": stock_number,
                "stock_name": clean_text(row.get("STOCK NAME")),
                "weblink": clean_text(row.get("WEBLINK")),
                "price": clean_text(row.get("PRICE")),
            }

    return stock_master


def write_csv(filepath: Path, header, rows):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with filepath.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def normalize_date(date_str: str):
    for fmt in ("%Y/%d/%m", "%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d"), dt.year, dt.month
        except ValueError:
            continue

    raise ValueError(f"Unsupported date format: {date_str}")


def build_stock_lookup(raw_data):
    return {
        entry["stock code"]: entry.get("stock data", {})
        for entry in raw_data
        if "stock code" in entry
    }


def build_metric_path(parent_path: str | None, metric_name: str) -> str:
    metric_name = clean_text(metric_name)
    if parent_path:
        return f"{parent_path} > {metric_name}"
    return metric_name


def process_metric(
    stock_number,
    statement_name,
    metric_name,
    metric_data,
    parent_metric_path,
    metric_rows_map,
    date_rows_map,
    fact_rows,
):
    metric_name = clean_text(metric_name)
    statement_name = clean_text(statement_name)
    metric_path = build_metric_path(parent_metric_path, metric_name)

    if metric_path not in metric_rows_map:
        metric_rows_map[metric_path] = {
            "metric_name": metric_name,
            "statement_name": statement_name,
            "metric_path": metric_path,
            "parent_metric_path": parent_metric_path,
        }

    if not isinstance(metric_data, dict):
        return

    if "data" in metric_data:
        value_map = metric_data["data"]
        child_items = [(k, v) for k, v in metric_data.items() if k != "data"]
    else:
        value_map = metric_data
        child_items = []

    for date_str, value in value_map.items():
        if value in ("-", "", None):
            continue

        normalized_date, year, month = normalize_date(date_str)

        if normalized_date not in date_rows_map:
            date_rows_map[normalized_date] = {
                "full_date": normalized_date,
                "year": year,
                "month": month,
            }

        try:
            numeric_value = float(str(value).replace(",", ""))
        except (ValueError, TypeError):
            continue

        fact_rows.append([
            normalize_stock_number(stock_number),
            statement_name,
            metric_path,
            normalized_date,
            numeric_value,
        ])

    for child_metric_name, child_metric_data in child_items:
        process_metric(
            stock_number=stock_number,
            statement_name=statement_name,
            metric_name=child_metric_name,
            metric_data=child_metric_data,
            parent_metric_path=metric_path,
            metric_rows_map=metric_rows_map,
            date_rows_map=date_rows_map,
            fact_rows=fact_rows,
        )


def run_etl():
    raw_data = load_json(FINANCIAL_JSON)
    stock_master = load_stock_master(STOCK_MASTER_CSV)
    stock_lookup = build_stock_lookup(raw_data)

    statement_names = set()
    metric_rows_map = {}
    date_rows_map = {}
    fact_rows = []

    for stock_code, master in stock_master.items():
        stock_data = stock_lookup.get(stock_code)
        if not stock_data:
            continue

        stock_number = normalize_stock_number(master["stock_number"])

        for statement_name, statement_data in stock_data.items():
            statement_name = clean_text(statement_name)
            statement_names.add(statement_name)

            if not isinstance(statement_data, dict):
                continue

            for metric_name, metric_data in statement_data.items():
                process_metric(
                    stock_number=stock_number,
                    statement_name=statement_name,
                    metric_name=metric_name,
                    metric_data=metric_data,
                    parent_metric_path=None,
                    metric_rows_map=metric_rows_map,
                    date_rows_map=date_rows_map,
                    fact_rows=fact_rows,
                )

    dim_stock_rows = []
    for _, master in stock_master.items():
        dim_stock_rows.append([
            normalize_stock_number(master["stock_number"]),
            clean_text(master["stock_code"]),
            clean_text(master.get("stock_name", "")),
            clean_text(master.get("weblink", "")),
            clean_text(master.get("price", "")),
        ])

    dim_statement_rows = [[statement_name] for statement_name in statement_names]

    dim_metric_rows = []
    for metric_path, info in metric_rows_map.items():
        dim_metric_rows.append([
            clean_text(info["metric_name"]),
            clean_text(info["statement_name"]),
            clean_text(info["metric_path"]),
            clean_text(info["parent_metric_path"]),
        ])

    dim_date_rows = []
    for _, info in date_rows_map.items():
        dim_date_rows.append([
            info["full_date"],
            info["year"],
            info["month"],
        ])

    # Deduplicate facts in case the source repeats entries
    fact_rows = sorted(set(tuple(row) for row in fact_rows))

    dim_stock_rows = sorted(set(tuple(row) for row in dim_stock_rows))
    dim_statement_rows = sorted(set(tuple(row) for row in dim_statement_rows))
    dim_metric_rows = sorted(set(tuple(row) for row in dim_metric_rows))
    dim_date_rows = sorted(set(tuple(row) for row in dim_date_rows))

    write_csv(
        DIM_STOCK_CSV,
        ["stock_number", "stock_code", "stock_name", "weblink", "price"],
        dim_stock_rows,
    )

    write_csv(
        DIM_STATEMENT_CSV,
        ["statement_name"],
        dim_statement_rows,
    )

    write_csv(
        DIM_METRIC_CSV,
        ["metric_name", "statement_name", "metric_path", "parent_metric_path"],
        dim_metric_rows,
    )

    write_csv(
        DIM_DATE_CSV,
        ["full_date", "year", "month"],
        dim_date_rows,
    )

    write_csv(
        FACT_CSV,
        ["stock_number", "statement_name", "metric_path", "full_date", "value"],
        fact_rows,
    )

    print("✅ ETL completed successfully!")
    print(f"Stocks: {len(dim_stock_rows)}")
    print(f"Statements: {len(dim_statement_rows)}")
    print(f"Metrics: {len(dim_metric_rows)}")
    print(f"Dates: {len(dim_date_rows)}")
    print(f"Facts: {len(fact_rows)}")


if __name__ == "__main__":
    run_etl()