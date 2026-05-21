import pandas as pd
from pathlib import Path
from decimal import Decimal

from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from app.models.auth.user import User
from app.models.stock.dim_stock import DimStock
from app.models.stock.dim_date import DimDate
from app.models.stock.dim_statement import DimStatement
from app.models.stock.dim_metric import DimMetric
from app.models.stock.fact_financial_values import FactFinancialValues


import logging

logger = logging.getLogger(__name__)


CSV_DATA_PATH = Path("/home/fbinalex/NPI-IDBMS/db/stock/transformed_data/b1")



def clean_text(value):
    if pd.isna(value):
        return None

    if value is None:
        return None

    value = str(value).strip()

    if value == "":
        return None

    if value.lower() in {"nan", "<na>", "none", "null", "nat"}:
        return None

    return value


def clean_stock_number(value):
    value = clean_text(value)
    if value is None:
        return None
    return value.zfill(4)


def to_decimal(value):
    cleaned = clean_text(value)
    if cleaned is None:
        return None

    try:
        return Decimal(str(cleaned).replace(",", ""))
    except Exception:
        return None


def bulk_insert_do_nothing(db: Session, model, records, conflict_cols=None):
    if not records:
        return 0

    stmt = insert(model).values(records)
    if conflict_cols:
        stmt = stmt.on_conflict_do_nothing(index_elements=conflict_cols)

    result = db.execute(stmt)
    db.commit()
    return result.rowcount or 0


def seed_dim_stock(db: Session):
    try:
        logger.info("📥 Seeding dim_stock...")

        df = pd.read_csv(
            CSV_DATA_PATH / "dim_stock.csv",
            dtype={
                "stock_code": "string",
                "stock_number": "string",
                "stock_name": "string",
                "weblink": "string",
                "price": "string",
            },
            keep_default_na=False,
        )

        df["stock_code"] = df["stock_code"].apply(clean_text)
        df["stock_number"] = df["stock_number"].apply(clean_stock_number)
        df["stock_name"] = df["stock_name"].apply(clean_text)
        df["weblink"] = df["weblink"].apply(clean_text)
        df["price"] = df["price"].apply(to_decimal)

        df = df.dropna(subset=["stock_number", "stock_code", "stock_name"]).copy()
        df = df.drop_duplicates(subset=["stock_number"]).copy()

        records = df.to_dict(orient="records")

        inserted = bulk_insert_do_nothing(
            db,
            DimStock,
            records,
            conflict_cols=["stock_number"],
        )

        logger.info(f"✅ dim_stock: {inserted} rows inserted")

    except Exception as e:
        db.rollback()
        logger.info(f"❌ dim_stock error: {e}")


def seed_dim_date(db: Session):
    try:
        logger.info("📥 Seeding dim_date...")

        df = pd.read_csv(CSV_DATA_PATH / "dim_date.csv", keep_default_na=False)
        df["full_date"] = pd.to_datetime(df["full_date"]).dt.date

        df = df.drop_duplicates(subset=["full_date"]).copy()

        records = df.to_dict(orient="records")

        inserted = bulk_insert_do_nothing(
            db,
            DimDate,
            records,
            conflict_cols=["full_date"],
        )

        logger.info(f"✅ dim_date: {inserted} rows inserted")

    except Exception as e:
        db.rollback()
        logger.info(f"❌ dim_date error: {e}")


def seed_dim_statement(db: Session):
    try:
        logger.info("📥 Seeding dim_statement...")

        df = pd.read_csv(CSV_DATA_PATH / "dim_statement.csv", keep_default_na=False)
        df["statement_name"] = df["statement_name"].apply(clean_text)

        df = df.dropna(subset=["statement_name"]).copy()
        df = df.drop_duplicates(subset=["statement_name"]).copy()

        records = df.to_dict(orient="records")

        inserted = bulk_insert_do_nothing(
            db,
            DimStatement,
            records,
            conflict_cols=["statement_name"],
        )

        logger.info(f"✅ dim_statement: {inserted} rows inserted")

    except Exception as e:
        db.rollback()
        logger.info(f"❌ dim_statement error: {e}")


def seed_dim_metric(db: Session):
    try:
        logger.info("📥 Seeding dim_metric...")

        df = pd.read_csv(
            CSV_DATA_PATH / "dim_metric.csv",
            dtype={
                "metric_name": object,
                "statement_name": object,
                "metric_path": object,
                "parent_metric_path": object,
            },
            keep_default_na=False,
        )

        df["metric_name"] = df["metric_name"].apply(clean_text)
        df["statement_name"] = df["statement_name"].apply(clean_text)
        df["metric_path"] = df["metric_path"].apply(clean_text)

        def normalize_parent_path(x):
            if pd.isna(x):
                return None
            if x is None:
                return None

            x = str(x).strip()

            if x == "":
                return None

            if x.lower() in {"nan", "<na>", "none", "null", "nat"}:
                return None

            return x

        df["parent_metric_path"] = df["parent_metric_path"].apply(normalize_parent_path)

        # force all pandas missing values to real Python None
        df = df.astype(object)
        df = df.where(pd.notna(df), None)

        df = df.dropna(subset=["metric_name", "statement_name", "metric_path"]).copy()
        df = df.drop_duplicates(subset=["metric_path"]).copy()

        # sort by tree depth first for stability
        df["depth"] = df["metric_path"].apply(lambda x: x.count(" > ") if x else 0)
        df = df.sort_values(by=["depth", "metric_path"], na_position="first").copy()
        df = df.drop(columns=["depth"])

        statement_map = {
            clean_text(s.statement_name): s.statement_id
            for s in db.query(DimStatement).all()
        }

        existing_metrics = db.query(DimMetric).all()
        metric_map = {
            clean_text(m.metric_path): m
            for m in existing_metrics
            if clean_text(m.metric_path) is not None
        }

        pending_rows = df.to_dict(orient="records")

        logger.info("🔎 Sample parent_metric_path values after normalization:")
        for row in pending_rows[:10]:
            logger.info(
                f"   metric={repr(row['metric_path'])} "
                f"parent={repr(row['parent_metric_path'])} "
                f"type={type(row['parent_metric_path']).__name__}"
            )

        inserted_count = 0
        skipped_existing = 0
        round_num = 0

        while pending_rows:
            round_num += 1
            inserted_this_round = 0
            next_pending = []

            for row in pending_rows:
                metric_name = row["metric_name"]
                statement_name = row["statement_name"]
                metric_path = row["metric_path"]
                parent_metric_path = row["parent_metric_path"]

                if metric_path in metric_map:
                    skipped_existing += 1
                    continue

                statement_id = statement_map.get(statement_name)
                if statement_id is None:
                    logger.info(f"⚠️ statement_name not found, skipping metric: {statement_name}")
                    continue

                parent_metric_id = None

                # root metric
                if parent_metric_path is not None:
                    parent_metric = metric_map.get(parent_metric_path)

                    if parent_metric is None:
                        next_pending.append(row)
                        continue

                    if parent_metric.statement_id != statement_id:
                        logger.info(
                            f"⚠️ parent/child statement mismatch, skipping metric: "
                            f"parent={repr(parent_metric_path)} child={repr(metric_path)}"
                        )
                        continue

                    parent_metric_id = parent_metric.metric_id

                new_metric = DimMetric(
                    metric_name=metric_name,
                    metric_path=metric_path,
                    statement_id=statement_id,
                    parent_metric_id=parent_metric_id,
                )

                db.add(new_metric)
                db.flush()

                metric_map[metric_path] = new_metric
                inserted_this_round += 1
                inserted_count += 1

            db.commit()
            logger.info(f"✅ dim_metric round {round_num}: {inserted_this_round} rows inserted")

            if inserted_this_round == 0:
                if next_pending:
                    logger.info("⚠️ Could not resolve some metric parent relationships:")
                    for row in next_pending[:20]:
                        logger.info(
                            f"   child={repr(row['metric_path'])} "
                            f"parent={repr(row['parent_metric_path'])}"
                        )
                    logger.info(f"⚠️ unresolved metric rows skipped: {len(next_pending)}")
                break

            pending_rows = next_pending

        logger.info(f"✅ dim_metric total inserted: {inserted_count}")
        logger.info(f"ℹ️ dim_metric already existing rows skipped: {skipped_existing}")

    except Exception as e:
        db.rollback()
        logger.info(f"❌ dim_metric error: {e}")


def seed_fact_financial_values(db: Session):
    try:
        logger.info("📥 Seeding fact_financial_values...")

        df = pd.read_csv(
            CSV_DATA_PATH / "fact_financial_values.csv",
            dtype={
                "stock_number": "string",
                "statement_name": "string",
                "metric_path": "string",
                "full_date": "string",
                "value": "string",
            },
            keep_default_na=False,
        )

        df["stock_number"] = df["stock_number"].apply(clean_stock_number)
        df["statement_name"] = df["statement_name"].apply(clean_text)
        df["metric_path"] = df["metric_path"].apply(clean_text)
        df["full_date"] = pd.to_datetime(df["full_date"]).dt.date
        df["value"] = df["value"].apply(to_decimal)

        df = df.dropna(
            subset=["stock_number", "statement_name", "metric_path", "full_date"]
        ).copy()

        stock_map = {
            clean_stock_number(x.stock_number): x.stock_id
            for x in db.query(DimStock).all()
        }
        statement_map = {
            clean_text(x.statement_name): x.statement_id
            for x in db.query(DimStatement).all()
        }
        date_map = {
            x.full_date: x.date_id
            for x in db.query(DimDate).all()
        }
        metric_map = {
            clean_text(x.metric_path): x.metric_id
            for x in db.query(DimMetric).all()
        }

        missing_stock = sorted(
            set(
                df.loc[
                    ~df["stock_number"].isin(stock_map.keys()),
                    "stock_number"
                ].dropna().tolist()
            )
        )
        if missing_stock:
            logger.info("⚠️ Missing stock_number in dim_stock (first 20):", missing_stock[:20])

        records = []
        skipped_rows = 0

        for row in df.to_dict(orient="records"):
            stock_id = stock_map.get(row["stock_number"])
            statement_id = statement_map.get(row["statement_name"])
            metric_id = metric_map.get(row["metric_path"])
            date_id = date_map.get(row["full_date"])

            if stock_id is None:
                skipped_rows += 1
                continue
            if statement_id is None:
                skipped_rows += 1
                continue
            if metric_id is None:
                skipped_rows += 1
                continue
            if date_id is None:
                skipped_rows += 1
                continue

            records.append(
                {
                    "stock_id": stock_id,
                    "metric_id": metric_id,
                    "statement_id": statement_id,
                    "date_id": date_id,
                    "value": row["value"],
                }
            )

        inserted = bulk_insert_do_nothing(
            db,
            FactFinancialValues,
            records,
            conflict_cols=["stock_id", "metric_id", "statement_id", "date_id"],
        )

        logger.info(f"✅ fact_financial_values: {inserted} rows inserted")
        logger.info(f"ℹ️ fact_financial_values skipped rows: {skipped_rows}")

    except Exception as e:
        db.rollback()
        logger.info(f"❌ fact_financial_values error: {e}")


def seed_db(db: Session):
    logger.info("\n📊 Starting database seeding...\n")

    try:
        user_records = [
            {"email": "rishin@decade.com", "password": "1234"},
            {"email": "bob@example.com", "password": "hashed_password2"},
        ]
        bulk_insert_do_nothing(db, User, user_records, conflict_cols=["email"])

        logger.info("✅ Mock user data seeded")

    except Exception as e:
        db.rollback()
        logger.info(f"⚠️ Mock data error: {e}")

    seed_dim_statement(db)
    seed_dim_stock(db)
    seed_dim_date(db)
    seed_dim_metric(db)
    seed_fact_financial_values(db)

    logger.info("\n✅ Database seeding completed!\n")