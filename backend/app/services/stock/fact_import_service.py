import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy import tuple_, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.stock.dim_stock import DimStock
from app.models.stock.dim_metric import DimMetric
from app.models.stock.dim_statement import DimStatement
from app.models.stock.dim_date import DimDate
from app.models.stock.fact_financial_values import FactFinancialValues
from app.models.stock.import_job import ImportJob
from app.services.storage.file_storage_service import FileStorageService


class FinancialFactsImportService:
    CHUNK_SIZE = 1000
    MAX_ERROR_MESSAGES = 100
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 10 MB

    UPSERT_COLUMNS = [
        "stock_id",
        "metric_id",
        "statement_id",
        "date_id",
    ]

    def __init__(self, db: Session):
        self.db = db
        self.file_storage = FileStorageService(db)

    async def import_csv(
        self,
        file: UploadFile,
        dry_run: bool = False,
        replace_all: bool = False,
        imported_by_id: int | None = None,
    ) -> dict[str, Any]:
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

        content = await file.read()
        if len(content) > self.MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large.")

        try:
            decoded = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="CSV file must be UTF-8 encoded.")

        reader = csv.DictReader(io.StringIO(decoded))

        if not reader.fieldnames:
            raise HTTPException(status_code=400, detail="CSV file is empty or invalid.")

        self._validate_required_columns(reader.fieldnames)

        parsed_rows: list[dict[str, Any]] = []
        errors: list[str] = []
        skipped = 0
        duplicates_in_file = 0
        total_rows = 0
        seen_keys = set()

        for row_number, row in enumerate(reader, start=2):
            total_rows += 1

            try:
                record = self._parse_row(row)
                key = (
                    record["stock_key_type"],
                    record["stock_key_value"],
                    record["metric_key_type"],
                    record["metric_key_value"],
                    record["statement_name"],
                    record["full_date"],
                )

                if key in seen_keys:
                    duplicates_in_file += 1
                    continue

                seen_keys.add(key)
                record["_row_number"] = row_number
                parsed_rows.append(record)

            except ValueError as e:
                skipped += 1
                if len(errors) < self.MAX_ERROR_MESSAGES:
                    errors.append(f"Row {row_number}: {str(e)}")
            except Exception as e:
                skipped += 1
                if len(errors) < self.MAX_ERROR_MESSAGES:
                    errors.append(f"Row {row_number}: unexpected error - {str(e)}")

        valid_rows, fk_errors = self._resolve_business_keys(parsed_rows)

        if fk_errors:
            skipped += len(fk_errors)
            remaining_slots = self.MAX_ERROR_MESSAGES - len(errors)
            if remaining_slots > 0:
                errors.extend(fk_errors[:remaining_slots])

        if not valid_rows and not errors:
            raise HTTPException(status_code=400, detail="No valid rows found in CSV.")

        would_insert, would_update, would_unchanged, changed_rows = self._estimate_row_changes(valid_rows)

        if replace_all:
            would_insert = len(valid_rows)
            would_update = 0
            would_unchanged = 0

        if dry_run:
            self.db.rollback()
            return {
                "message": "Dry run completed" if not errors else "Dry run completed with issues",
                "dry_run": True,
                "table_name": "fact_financial_values",
                "filename": file.filename,
                "replace_all": replace_all,
                "inserted": 0,
                "updated": 0,
                "unchanged": 0,
                "would_insert": would_insert,
                "would_update": would_update,
                "would_unchanged": would_unchanged,
                "skipped": skipped,
                "duplicates_in_file": duplicates_in_file,
                "total_rows": total_rows,
                "processed_rows": len(valid_rows),
                "status": "completed",
                "errors": errors,
                "changed_rows_preview": [] if replace_all else changed_rows[:20],
            }

        try:
            if replace_all:
                self.db.query(FactFinancialValues).delete()

            inserted, updated, unchanged = self._bulk_upsert(
                valid_rows,
                expected_inserted=would_insert,
                expected_updated=would_update,
                expected_unchanged=would_unchanged,
                replace_all=replace_all,
            )
            self.db.commit()

        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to import CSV: {str(e)}")

        result = {
            "message": "Import completed" if not errors else "Import completed with issues",
            "dry_run": False,
            "table_name": "fact_financial_values",
            "filename": file.filename,
            "replace_all": replace_all,
            "inserted": inserted,
            "updated": updated,
            "unchanged": unchanged,
            "skipped": skipped,
            "duplicates_in_file": duplicates_in_file,
            "total_rows": total_rows,
            "processed_rows": len(valid_rows),
            "status": "completed",
            "errors": errors,
        }

        if self._should_log_import(result):
            stored_file = None
            try:
                stored_file = self.file_storage.save_uploaded_file(
                    content=content,
                    original_filename=file.filename or "import.csv",
                    mime_type=file.content_type,
                    uploaded_by_id=imported_by_id,
                )

                job = self._log_import_job(
                    result,
                    imported_by_id=imported_by_id,
                    file_id=stored_file.file_id,
                )
                result["import_job_id"] = job.import_job_id

            except Exception:
                self.db.rollback()
                if stored_file is not None:
                    try:
                        self.file_storage.delete_stored_file(stored_file)
                        self.db.commit()
                    except Exception:
                        self.db.rollback()
                raise

        return result

    def _should_log_import(self, result: dict[str, Any]) -> bool:
        if result.get("dry_run", False):
            return False
        return (result.get("inserted", 0) > 0) or (result.get("updated", 0) > 0)

    def _log_import_job(
        self,
        result: dict[str, Any],
        imported_by_id: int | None = None,
        file_id: int | None = None,
    ) -> ImportJob:
        job = ImportJob(
            table_name=result.get("table_name"),
            filename=result.get("filename"),
            file_type="csv",
            replace_all=result.get("replace_all", False),
            inserted=result.get("inserted", 0),
            updated=result.get("updated", 0),
            unchanged=result.get("unchanged", 0),
            skipped=result.get("skipped", 0),
            duplicates_in_file=result.get("duplicates_in_file", 0),
            total_rows=result.get("total_rows", 0),
            processed_rows=result.get("processed_rows", 0),
            status=result.get("status", "completed"),
            message=result.get("message"),
            imported_by_id=imported_by_id,
            file_id=file_id,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def _validate_required_columns(self, fieldnames: list[str]) -> None:
        cols = set(fieldnames)

        missing_groups = []

        if "statement_name" not in cols:
            missing_groups.append("statement_name")

        if "full_date" not in cols:
            missing_groups.append("full_date")

        if "value" not in cols:
            missing_groups.append("value")

        if not (("stock_code" in cols) or ("stock_number" in cols)):
            missing_groups.append("stock_code or stock_number")

        if not (("metric_path" in cols) or ("metric_name" in cols)):
            missing_groups.append("metric_path or metric_name")

        if missing_groups:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_groups)}",
            )

    def _normalize_str(self, value: Any) -> str | None:
        if value is None:
            return None
        text_value = str(value).strip()
        return text_value if text_value else None

    def _normalize_path(self, value: Any) -> str | None:
        raw = self._normalize_str(value)
        if raw is None:
            return None
        normalized = " > ".join(part.strip() for part in raw.split(">") if part.strip())
        return normalized or None

    def _parse_date(self, field_name: str, value: Any):
        normalized = self._normalize_str(value)
        if normalized is None:
            raise ValueError(f"{field_name} is required")

        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(normalized, fmt).date()
            except ValueError:
                pass

        raise ValueError(f"{field_name} must be a valid date")

    def _parse_decimal(self, field_name: str, value: Any):
        normalized = self._normalize_str(value)
        if normalized is None:
            return None
        try:
            return Decimal(normalized).quantize(
                Decimal("0.0001"),
                rounding=ROUND_HALF_UP,
            )
        except InvalidOperation:
            raise ValueError(f"{field_name} must be a valid decimal")

    def _parse_row(self, row: dict[str, Any]) -> dict[str, Any]:
        statement_name = self._normalize_str(row.get("statement_name"))
        if statement_name is None:
            raise ValueError("statement_name is required")

        stock_code = self._normalize_str(row.get("stock_code"))
        stock_number = self._normalize_str(row.get("stock_number"))

        if stock_code:
            stock_key_type = "stock_code"
            stock_key_value = stock_code
        elif stock_number:
            stock_key_type = "stock_number"
            stock_key_value = stock_number
        else:
            raise ValueError("either stock_code or stock_number is required")

        metric_path = self._normalize_path(row.get("metric_path"))
        metric_name = self._normalize_str(row.get("metric_name"))

        if metric_path:
            metric_key_type = "metric_path"
            metric_key_value = metric_path
        elif metric_name:
            metric_key_type = "metric_name"
            metric_key_value = metric_name
        else:
            raise ValueError("either metric_path or metric_name is required")

        return {
            "stock_key_type": stock_key_type,
            "stock_key_value": stock_key_value,
            "metric_key_type": metric_key_type,
            "metric_key_value": metric_key_value,
            "statement_name": statement_name,
            "full_date": self._parse_date("full_date", row.get("full_date")),
            "value": self._parse_decimal("value", row.get("value")),
        }

    def _resolve_business_keys(
        self,
        rows: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        if not rows:
            return [], []

        stock_codes = {
            row["stock_key_value"]
            for row in rows
            if row["stock_key_type"] == "stock_code"
        }
        stock_numbers = {
            row["stock_key_value"]
            for row in rows
            if row["stock_key_type"] == "stock_number"
        }
        metric_paths = {
            row["metric_key_value"]
            for row in rows
            if row["metric_key_type"] == "metric_path"
        }
        metric_names = {
            row["metric_key_value"]
            for row in rows
            if row["metric_key_type"] == "metric_name"
        }
        statement_names = {row["statement_name"] for row in rows}
        full_dates = {row["full_date"] for row in rows}

        valid_stock_code_map = {
            x.stock_code: x.stock_id
            for x in self.db.query(DimStock).filter(DimStock.stock_code.in_(stock_codes)).all()
        }

        valid_stock_number_map = {
            str(x.stock_number): x.stock_id
            for x in self.db.query(DimStock).filter(DimStock.stock_number.in_(stock_numbers)).all()
        }

        valid_metric_path_map = {
            self._normalize_path(x.metric_path): x.metric_id
            for x in self.db.query(DimMetric).filter(DimMetric.metric_path.in_(metric_paths)).all()
        }

        valid_metric_name_rows = (
            self.db.query(DimMetric.metric_name, DimMetric.metric_id)
            .filter(DimMetric.metric_name.in_(metric_names))
            .all()
        )

        valid_metric_name_map: dict[str, list[int]] = {}
        for metric_name, metric_id in valid_metric_name_rows:
            valid_metric_name_map.setdefault(metric_name, []).append(metric_id)

        valid_statement_map = {
            x.statement_name: x.statement_id
            for x in self.db.query(DimStatement).filter(DimStatement.statement_name.in_(statement_names)).all()
        }

        valid_date_map = {
            x.full_date: x.date_id
            for x in self.db.query(DimDate).filter(DimDate.full_date.in_(full_dates)).all()
        }

        valid_rows: list[dict[str, Any]] = []
        errors: list[str] = []

        for row in rows:
            row_number = row["_row_number"]

            if row["stock_key_type"] == "stock_code":
                stock_id = valid_stock_code_map.get(row["stock_key_value"])
                if stock_id is None:
                    errors.append(
                        f"Row {row_number}: stock_code '{row['stock_key_value']}' does not exist in dim_stock"
                    )
                    continue
            else:
                stock_id = valid_stock_number_map.get(row["stock_key_value"])
                if stock_id is None:
                    errors.append(
                        f"Row {row_number}: stock_number '{row['stock_key_value']}' does not exist in dim_stock"
                    )
                    continue

            if row["metric_key_type"] == "metric_path":
                metric_id = valid_metric_path_map.get(row["metric_key_value"])
                if metric_id is None:
                    errors.append(
                        f"Row {row_number}: metric_path '{row['metric_key_value']}' does not exist in dim_metric"
                    )
                    continue
            else:
                metric_ids = valid_metric_name_map.get(row["metric_key_value"], [])
                if not metric_ids:
                    errors.append(
                        f"Row {row_number}: metric_name '{row['metric_key_value']}' does not exist in dim_metric"
                    )
                    continue
                if len(metric_ids) > 1:
                    errors.append(
                        f"Row {row_number}: metric_name '{row['metric_key_value']}' is ambiguous; use metric_path instead"
                    )
                    continue
                metric_id = metric_ids[0]

            statement_id = valid_statement_map.get(row["statement_name"])
            if statement_id is None:
                errors.append(
                    f"Row {row_number}: statement_name '{row['statement_name']}' does not exist in dim_statement"
                )
                continue

            date_id = valid_date_map.get(row["full_date"])
            if date_id is None:
                errors.append(
                    f"Row {row_number}: full_date '{row['full_date']}' does not exist in dim_date"
                )
                continue

            clean_row = {
                "stock_id": stock_id,
                "metric_id": metric_id,
                "statement_id": statement_id,
                "date_id": date_id,
                "value": row["value"],
            }
            valid_rows.append(clean_row)

        return valid_rows, errors

    def _values_differ(self, existing_value, incoming_value) -> bool:
        if existing_value is None and incoming_value is None:
            return False
        if existing_value is None or incoming_value is None:
            return True

        existing_normalized = Decimal(existing_value).quantize(Decimal("0.0001"))
        incoming_normalized = Decimal(incoming_value).quantize(Decimal("0.0001"))

        return existing_normalized != incoming_normalized

    def _estimate_row_changes(
        self,
        rows: list[dict[str, Any]],
    ) -> tuple[int, int, int, list[dict[str, Any]]]:
        if not rows:
            return 0, 0, 0, []

        would_insert = 0
        would_update = 0
        would_unchanged = 0
        changed_rows: list[dict[str, Any]] = []

        for i in range(0, len(rows), self.CHUNK_SIZE):
            chunk = rows[i : i + self.CHUNK_SIZE]

            keys = [
                (
                    row["stock_id"],
                    row["metric_id"],
                    row["statement_id"],
                    row["date_id"],
                )
                for row in chunk
            ]

            existing_rows = (
                self.db.query(
                    FactFinancialValues.stock_id,
                    FactFinancialValues.metric_id,
                    FactFinancialValues.statement_id,
                    FactFinancialValues.date_id,
                    FactFinancialValues.value,
                )
                .filter(
                    tuple_(
                        FactFinancialValues.stock_id,
                        FactFinancialValues.metric_id,
                        FactFinancialValues.statement_id,
                        FactFinancialValues.date_id,
                    ).in_(keys)
                )
                .all()
            )

            existing_map = {
                (
                    row.stock_id,
                    row.metric_id,
                    row.statement_id,
                    row.date_id,
                ): row.value
                for row in existing_rows
            }

            for incoming in chunk:
                key = (
                    incoming["stock_id"],
                    incoming["metric_id"],
                    incoming["statement_id"],
                    incoming["date_id"],
                )

                incoming_value = incoming["value"]

                if key not in existing_map:
                    would_insert += 1
                    continue

                existing_value = existing_map[key]

                if self._values_differ(existing_value, incoming_value):
                    would_update += 1
                    changed_rows.append(
                        {
                            "stock_id": incoming["stock_id"],
                            "metric_id": incoming["metric_id"],
                            "statement_id": incoming["statement_id"],
                            "date_id": incoming["date_id"],
                            "existing_value": str(existing_value) if existing_value is not None else None,
                            "incoming_value": str(incoming_value) if incoming_value is not None else None,
                        }
                    )
                else:
                    would_unchanged += 1

        return would_insert, would_update, would_unchanged, changed_rows

    def _bulk_upsert(
        self,
        rows: list[dict[str, Any]],
        expected_inserted: int,
        expected_updated: int,
        expected_unchanged: int,
        replace_all: bool = False,
    ) -> tuple[int, int, int]:
        if not rows:
            return 0, 0, 0

        for i in range(0, len(rows), self.CHUNK_SIZE):
            chunk = rows[i : i + self.CHUNK_SIZE]

            stmt = insert(FactFinancialValues).values(chunk)

            if replace_all:
                stmt = stmt.on_conflict_do_nothing(
                    index_elements=self.UPSERT_COLUMNS,
                )
            else:
                stmt = stmt.on_conflict_do_update(
                    index_elements=self.UPSERT_COLUMNS,
                    set_={
                        "value": stmt.excluded.value,
                    },
                    where=text("fact_financial_values.value IS DISTINCT FROM excluded.value"),
                )

            self.db.execute(stmt)

        return expected_inserted, expected_updated, expected_unchanged