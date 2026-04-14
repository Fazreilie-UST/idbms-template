import csv
import io
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy import or_, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.stock.dim_stock import DimStock
from app.models.stock.dim_date import DimDate
from app.models.stock.dim_statement import DimStatement
from app.models.stock.dim_metric import DimMetric
from app.models.stock.fact_financial_values import FactFinancialValues
from app.models.stock.import_job import ImportJob
from app.models.storage.stored_file import StoredFile
from app.services.storage.file_storage_service import FileStorageService


class DimensionImportService:
    CHUNK_SIZE = 1000
    MAX_ERROR_MESSAGES = 100
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

    MODEL_MAP = {
        "dim_stock": {
            "model": DimStock,
            "required_columns": {"stock_code", "stock_number", "stock_name"},
            "upsert_columns": ["stock_code"],
            "all_columns": {
                "stock_code",
                "stock_number",
                "stock_name",
                "weblink",
                "price",
            },
        },
        "dim_date": {
            "model": DimDate,
            "required_columns": {"full_date", "year", "month"},
            "upsert_columns": ["full_date"],
            "all_columns": {"full_date", "year", "month"},
        },
        "dim_statement": {
            "model": DimStatement,
            "required_columns": {"statement_name"},
            "upsert_columns": ["statement_name"],
            "all_columns": {"statement_name"},
        },
        "dim_metric": {
            "model": DimMetric,
            "required_columns": {"metric_name", "statement_name", "metric_path"},
            "upsert_columns": ["metric_path"],
            "all_columns": {
                "metric_name",
                "statement_name",
                "parent_metric_path",
                "metric_path",
            },
        },
    }

    FACT_REFERENCE_MAP = {
        "dim_date": FactFinancialValues.date_id,
        "dim_stock": FactFinancialValues.stock_id,
        "dim_statement": FactFinancialValues.statement_id,
        "dim_metric": FactFinancialValues.metric_id,
    }

    def __init__(self, db: Session):
        self.db = db
        self.file_storage = FileStorageService(db)

    async def import_csv(
        self,
        table_name: str,
        file: UploadFile,
        dry_run: bool = False,
        replace_all: bool = False,
        imported_by_id: int | None = None,
    ) -> dict[str, Any]:
        if table_name not in self.MODEL_MAP:
            raise HTTPException(status_code=400, detail=f"Unsupported table: {table_name}")

        config = self.MODEL_MAP[table_name]
        model = config["model"]
        required_columns = config["required_columns"]
        upsert_columns = config["upsert_columns"]
        allowed_columns = config["all_columns"]

        filename = file.filename or ""
        if not filename.lower().endswith(".csv"):
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

        missing = required_columns - set(reader.fieldnames)
        if missing:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(sorted(missing))}",
            )

        parsed_rows: list[dict[str, Any]] = []
        errors: list[str] = []
        skipped = 0
        duplicates_in_file = 0
        total_rows = 0
        seen_keys: set[tuple[Any, ...]] = set()
        parser_error_counts: dict[str, int] = {}

        for row_number, row in enumerate(reader, start=2):
            total_rows += 1
            try:
                parsed = self._parse_row(table_name, row, allowed_columns)
                key = tuple(parsed[col] for col in upsert_columns)

                if key in seen_keys:
                    duplicates_in_file += 1
                    continue

                seen_keys.add(key)
                parsed_rows.append(parsed)

            except ValueError as e:
                skipped += 1
                msg = str(e)
                parser_error_counts[msg] = parser_error_counts.get(msg, 0) + 1
                if len(errors) < self.MAX_ERROR_MESSAGES:
                    errors.append(f"Row {row_number}: {msg}")

        if table_name == "dim_metric":
            parsed_rows = self._sort_dim_metric_rows(parsed_rows)

        valid_rows, fk_errors = self._validate_foreign_keys(table_name, parsed_rows)

        if fk_errors:
            skipped += len(fk_errors)
            remaining_slots = self.MAX_ERROR_MESSAGES - len(errors)
            if remaining_slots > 0:
                errors.extend(fk_errors[:remaining_slots])

        if replace_all:
            change_set = {
                "to_insert": valid_rows,
                "to_update": [],
                "unchanged": 0,
            }
        else:
            if table_name == "dim_metric":
                change_set = self._classify_dim_metric_rows(valid_rows)
            else:
                change_set = self._classify_rows(
                    table_name=table_name,
                    model=model,
                    rows=valid_rows,
                    upsert_columns=upsert_columns,
                )

        would_insert = len(change_set["to_insert"])
        would_update = len(change_set["to_update"])
        would_unchanged = change_set["unchanged"]

        if dry_run:
            self.db.rollback()
            return {
                "message": "Dry run completed" if not errors else "Dry run completed with issues",
                "dry_run": True,
                "table_name": table_name,
                "filename": filename,
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
                "validation_summary": {
                    "parser_errors": parser_error_counts,
                    "fk_error_count": len(fk_errors),
                },
                "errors": errors,
            }

        try:
            if replace_all:
                self._ensure_replace_all_is_safe(table_name)
                self.db.query(model).delete()
                self.db.flush()

            if table_name == "dim_metric":
                if replace_all:
                    inserted, updated = self._apply_dim_metric_changes(
                        to_insert=valid_rows,
                        to_update=[],
                    )
                    unchanged = 0
                else:
                    inserted, updated = self._apply_dim_metric_changes(
                        to_insert=change_set["to_insert"],
                        to_update=change_set["to_update"],
                    )
                    unchanged = change_set["unchanged"]
            else:
                inserted = self._bulk_insert_new_rows(
                    model=model,
                    rows=change_set["to_insert"],
                    upsert_columns=upsert_columns,
                )
                updated = self._bulk_update_changed_rows(
                    model=model,
                    rows=change_set["to_update"],
                    upsert_columns=upsert_columns,
                )
                unchanged = change_set["unchanged"]

            self.db.commit()

        except Exception as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Failed to import CSV: {str(e)}")

        result = {
            "message": "Import completed" if not errors else "Import completed with issues",
            "dry_run": False,
            "table_name": table_name,
            "filename": filename,
            "replace_all": replace_all,
            "inserted": inserted,
            "updated": updated,
            "unchanged": unchanged,
            "would_insert": 0,
            "would_update": 0,
            "would_unchanged": 0,
            "skipped": skipped,
            "duplicates_in_file": duplicates_in_file,
            "total_rows": total_rows,
            "processed_rows": len(valid_rows),
            "status": "completed",
            "validation_summary": {
                "parser_errors": parser_error_counts,
                "fk_error_count": len(fk_errors),
            },
            "errors": errors,
        }

        if self._should_log_import(result):
            stored_file = None
            try:
                stored_file = self.file_storage.save_uploaded_file(
                    content=content,
                    original_filename=filename,
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

    def _ensure_replace_all_is_safe(self, table_name: str) -> None:
        fact_fk_column = self.FACT_REFERENCE_MAP.get(table_name)
        if fact_fk_column is None:
            return

        fact_exists = (
            self.db.query(FactFinancialValues)
            .filter(fact_fk_column.isnot(None))
            .first()
            is not None
        )

        if fact_exists:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"replace_all is not allowed for {table_name} because "
                    "fact_financial_values still references rows in this dimension. "
                    "Delete or rebuild dependent fact rows first."
                ),
            )

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

    def _normalize_stock_number(self, value: str | None) -> str | None:
        if value is None:
            return None
        value = str(value).strip()
        if value.endswith(".0"):
            return value[:-2]
        return value

    def _normalize_path(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " > ".join(part.strip() for part in str(value).split(">") if part.strip())
        return normalized or None

    def _metric_depth(self, metric_path: str | None) -> int:
        normalized = self._normalize_path(metric_path)
        if not normalized:
            return 0
        return len(normalized.split(" > ")) - 1

    def _is_parent_path_of(self, parent_path: str | None, child_path: str | None) -> bool:
        parent = self._normalize_path(parent_path)
        child = self._normalize_path(child_path)

        if not parent or not child or parent == child:
            return False

        child_parts = child.split(" > ")
        parent_parts = parent.split(" > ")

        if len(parent_parts) >= len(child_parts):
            return False

        return child_parts[: len(parent_parts)] == parent_parts

    def _sort_dim_metric_rows(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        def sort_key(row: dict[str, Any]):
            metric_path = self._normalize_path(row.get("metric_path"))
            parent_path = self._normalize_path(row.get("parent_metric_path"))

            return (
                1 if parent_path else 0,
                self._metric_depth(metric_path),
                parent_path or "",
                metric_path or "",
                row.get("metric_name") or "",
            )

        return sorted(rows, key=sort_key)

    def _parse_row(
        self,
        table_name: str,
        row: dict[str, Any],
        allowed_columns: set[str],
    ) -> dict[str, Any]:
        parsed: dict[str, Any] = {}

        for column in allowed_columns:
            if column not in row:
                continue

            raw_value = row.get(column)
            value = None if raw_value is None or str(raw_value).strip() == "" else str(raw_value).strip()

            if table_name == "dim_stock":
                if column == "price":
                    parsed[column] = self._parse_decimal(value, column)
                else:
                    parsed[column] = value

            elif table_name == "dim_date":
                if column in {"year", "month"}:
                    parsed[column] = self._parse_int(value, column)
                elif column == "full_date":
                    parsed[column] = self._parse_date(value, column)

            elif table_name == "dim_statement":
                parsed[column] = value

            elif table_name == "dim_metric":
                if column in {"metric_path", "parent_metric_path"}:
                    parsed[column] = self._normalize_path(value)
                else:
                    parsed[column] = value

        return parsed

    def _parse_int(self, value: str | None, field: str, nullable: bool = False) -> int | None:
        if value is None:
            if nullable:
                return None
            raise ValueError(f"{field} is required")
        try:
            return int(value)
        except ValueError as exc:
            raise ValueError(f"{field} must be an integer") from exc

    def _parse_decimal(self, value: str | None, field: str):
        if value is None:
            return None
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"{field} must be a valid decimal") from exc

    def _parse_date(self, value: str | None, field: str):
        if value is None:
            raise ValueError(f"{field} is required")
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass
        raise ValueError(f"{field} must be a valid date (YYYY-MM-DD preferred)")

    def _validate_foreign_keys(
        self,
        table_name: str,
        rows: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[str]]:
        if not rows:
            return [], []

        if table_name == "dim_metric":
            statement_names = {row["statement_name"] for row in rows if row.get("statement_name")}
            valid_statements = {
                x.statement_name: x.statement_id
                for x in self.db.query(DimStatement).filter(DimStatement.statement_name.in_(statement_names)).all()
            }

            existing_metric_paths = {
                self._normalize_path(x.metric_path)
                for x in self.db.query(DimMetric.metric_path).all()
                if x.metric_path
            }

            incoming_metric_paths = {
                self._normalize_path(row.get("metric_path"))
                for row in rows
                if row.get("metric_path")
            }

            valid_rows = []
            errors = []

            for idx, row in enumerate(rows, start=1):
                statement_name = row.get("statement_name")
                metric_path = self._normalize_path(row.get("metric_path"))
                parent_metric_path = self._normalize_path(row.get("parent_metric_path"))

                if not metric_path:
                    errors.append(f"Parsed row {idx}: metric_path is required")
                    continue

                if statement_name not in valid_statements:
                    errors.append(
                        f"Parsed row {idx}: statement_name '{statement_name}' does not exist in dim_statement"
                    )
                    continue

                if parent_metric_path:
                    if parent_metric_path == metric_path:
                        errors.append(
                            f"Parsed row {idx}: parent_metric_path cannot be the same as metric_path"
                        )
                        continue

                    if not self._is_parent_path_of(parent_metric_path, metric_path):
                        errors.append(
                            f"Parsed row {idx}: parent_metric_path '{parent_metric_path}' "
                            f"is not a valid parent of metric_path '{metric_path}'"
                        )
                        continue

                    if (
                        parent_metric_path not in existing_metric_paths
                        and parent_metric_path not in incoming_metric_paths
                    ):
                        errors.append(
                            f"Parsed row {idx}: parent_metric_path '{parent_metric_path}' "
                            "does not exist in dim_metric or the current CSV file"
                        )
                        continue

                valid_rows.append(
                    {
                        "metric_name": row.get("metric_name"),
                        "metric_path": metric_path,
                        "parent_metric_path": parent_metric_path,
                        "statement_id": valid_statements[statement_name],
                    }
                )

            return valid_rows, errors

        return rows, []

    def _values_equal(self, table_name: str, field: str, existing_value, incoming_value) -> bool:
        if existing_value is None and incoming_value is None:
            return True
        if existing_value is None or incoming_value is None:
            return False

        if table_name == "dim_stock" and field == "stock_number":
            existing_norm = self._normalize_stock_number(str(existing_value))
            incoming_norm = self._normalize_stock_number(str(incoming_value))
            return existing_norm == incoming_norm

        return existing_value == incoming_value

    def _classify_dim_metric_rows(
        self,
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not rows:
            return {
                "to_insert": [],
                "to_update": [],
                "unchanged": 0,
            }

        metric_paths = [row["metric_path"] for row in rows]

        existing_rows = (
            self.db.query(DimMetric)
            .filter(DimMetric.metric_path.in_(metric_paths))
            .all()
        )

        all_metrics = self.db.query(DimMetric.metric_id, DimMetric.metric_path).all()
        id_to_path = {
            metric_id: self._normalize_path(metric_path)
            for metric_id, metric_path in all_metrics
            if metric_path
        }

        existing_map = {
            self._normalize_path(row.metric_path): row
            for row in existing_rows
        }

        to_insert: list[dict[str, Any]] = []
        to_update: list[dict[str, Any]] = []
        unchanged = 0

        for incoming in rows:
            key = self._normalize_path(incoming["metric_path"])
            existing_obj = existing_map.get(key)

            if existing_obj is None:
                to_insert.append(incoming)
                continue

            existing_parent_path = id_to_path.get(existing_obj.parent_metric_id)
            incoming_parent_path = self._normalize_path(incoming.get("parent_metric_path"))

            changed = any(
                [
                    existing_obj.metric_name != incoming.get("metric_name"),
                    existing_obj.statement_id != incoming.get("statement_id"),
                    self._normalize_path(existing_parent_path) != incoming_parent_path,
                ]
            )

            if changed:
                to_update.append(incoming)
            else:
                unchanged += 1

        return {
            "to_insert": to_insert,
            "to_update": to_update,
            "unchanged": unchanged,
        }

    def _classify_rows(
        self,
        table_name: str,
        model,
        rows: list[dict[str, Any]],
        upsert_columns: list[str],
    ) -> dict[str, Any]:
        if not rows:
            return {
                "to_insert": [],
                "to_update": [],
                "unchanged": 0,
            }

        to_insert: list[dict[str, Any]] = []
        to_update: list[dict[str, Any]] = []
        unchanged = 0

        for i in range(0, len(rows), self.CHUNK_SIZE):
            chunk = rows[i : i + self.CHUNK_SIZE]

            keys = [tuple(row[col] for col in upsert_columns) for row in chunk]
            db_columns = [getattr(model, col) for col in upsert_columns]

            existing_rows = (
                self.db.query(model)
                .filter(tuple_(*db_columns).in_(keys))
                .all()
            )

            existing_map = {
                tuple(getattr(row, col) for col in upsert_columns): row
                for row in existing_rows
            }

            for incoming in chunk:
                key = tuple(incoming[col] for col in upsert_columns)

                if key not in existing_map:
                    to_insert.append(incoming)
                    continue

                existing_obj = existing_map[key]
                changed = False

                for field, incoming_value in incoming.items():
                    existing_value = getattr(existing_obj, field)
                    if not self._values_equal(table_name, field, existing_value, incoming_value):
                        changed = True
                        break

                if changed:
                    to_update.append(incoming)
                else:
                    unchanged += 1

        return {
            "to_insert": to_insert,
            "to_update": to_update,
            "unchanged": unchanged,
        }

    def _apply_dim_metric_changes(
        self,
        to_insert: list[dict[str, Any]],
        to_update: list[dict[str, Any]],
    ) -> tuple[int, int]:
        if not to_insert and not to_update:
            return 0, 0

        insert_paths = {self._normalize_path(row["metric_path"]) for row in to_insert}
        update_paths = {self._normalize_path(row["metric_path"]) for row in to_update}

        combined_rows = self._sort_dim_metric_rows(to_insert + to_update)

        rows_by_depth: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in combined_rows:
            rows_by_depth[self._metric_depth(row.get("metric_path"))].append(row)

        inserted = 0
        updated = 0

        for depth in sorted(rows_by_depth.keys()):
            level_rows = rows_by_depth[depth]

            path_to_id = self._get_metric_path_to_id_map()

            resolved_inserts: list[dict[str, Any]] = []
            resolved_updates: list[dict[str, Any]] = []

            for row in level_rows:
                metric_path = self._normalize_path(row.get("metric_path"))
                parent_metric_path = self._normalize_path(row.get("parent_metric_path"))

                parent_metric_id = None
                if parent_metric_path:
                    parent_metric_id = path_to_id.get(parent_metric_path)
                    if parent_metric_id is None:
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"Unable to resolve parent_metric_path '{parent_metric_path}' "
                                f"for metric_path '{metric_path}'. Ensure parent rows are present first."
                            ),
                        )

                db_row = {
                    "metric_name": row.get("metric_name"),
                    "metric_path": metric_path,
                    "statement_id": row.get("statement_id"),
                    "parent_metric_id": parent_metric_id,
                }

                if metric_path in insert_paths:
                    resolved_inserts.append(db_row)
                elif metric_path in update_paths:
                    resolved_updates.append(db_row)

            if resolved_inserts:
                inserted += self._bulk_insert_new_rows(
                    model=DimMetric,
                    rows=resolved_inserts,
                    upsert_columns=["metric_path"],
                )

            if resolved_updates:
                updated += self._bulk_update_changed_rows(
                    model=DimMetric,
                    rows=resolved_updates,
                    upsert_columns=["metric_path"],
                )

            self.db.flush()

        return inserted, updated

    def _get_metric_path_to_id_map(self) -> dict[str, int]:
        rows = self.db.query(DimMetric.metric_id, DimMetric.metric_path).all()
        return {
            self._normalize_path(metric_path): metric_id
            for metric_id, metric_path in rows
            if metric_path
        }

    def _bulk_insert_new_rows(
        self,
        model,
        rows: list[dict[str, Any]],
        upsert_columns: list[str],
    ) -> int:
        if not rows:
            return 0

        inserted = 0

        for i in range(0, len(rows), self.CHUNK_SIZE):
            chunk = rows[i : i + self.CHUNK_SIZE]
            stmt = insert(model).values(chunk)
            stmt = stmt.on_conflict_do_nothing(index_elements=upsert_columns)
            self.db.execute(stmt)
            inserted += len(chunk)

        return inserted

    def _bulk_update_changed_rows(
        self,
        model,
        rows: list[dict[str, Any]],
        upsert_columns: list[str],
    ) -> int:
        if not rows:
            return 0

        updated = 0
        update_columns = [col for col in rows[0].keys() if col not in upsert_columns]

        if not update_columns:
            return 0

        for i in range(0, len(rows), self.CHUNK_SIZE):
            chunk = rows[i : i + self.CHUNK_SIZE]

            stmt = insert(model).values(chunk)
            set_map = {col: getattr(stmt.excluded, col) for col in update_columns}

            distinct_conditions = [
                getattr(model, col).is_distinct_from(getattr(stmt.excluded, col))
                for col in update_columns
            ]

            stmt = stmt.on_conflict_do_update(
                index_elements=upsert_columns,
                set_=set_map,
                where=or_(*distinct_conditions),
            )

            self.db.execute(stmt)
            updated += len(chunk)

        return updated