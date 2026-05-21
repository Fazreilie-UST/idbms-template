"""Shipping bulk import service.

Adapts the per-row parsing logic of :mod:`app.scripts.seed_shipments` to work
against an arbitrary uploaded Excel file with the caller-supplied SQLAlchemy
session. Emits per-row progress events via the optional ``progress_cb`` so the
API layer can stream updates back to the UI.

Caller (the API endpoint) is responsible for committing or rolling back the
session. On success ``import_file.status`` is set to ``success`` and ``summary``
is populated. On failure the import_file row is flipped to ``failed`` with the
error message stored on the row.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from sqlalchemy.orm import Session

from app.models.order.shipping_import_file import (
    ShippingImportFile,
    ShippingImportStatus,
)
from app.scripts import seed_shipments as ss


def count_shipments_in_file(file_path: Path) -> int:
    """Pre-count the total number of shipment data rows across all sheets.

    The frontend uses this to size the progress bar. Rows where the
    configured "config" column is empty are excluded (they're skipped during
    import anyway).
    """
    try:
        xls = pd.ExcelFile(file_path, engine="calamine")
    except Exception:
        return 0

    total = 0
    for sheet_name in xls.sheet_names:
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        except Exception:
            continue
        detected = ss.detect_header(df)
        if detected is None:
            continue
        header_row, col_map = detected
        data = df.iloc[header_row + 1 :]
        config_idx = col_map.get("config")
        if config_idx is None:
            continue
        for _, row in data.iterrows():
            if config_idx >= len(row):
                continue
            if ss.clean(row.iloc[config_idx]) is not None:
                total += 1
    return total


def _process_file(
    session: Session,
    file_path: Path,
    progress_cb: Callable[[str, dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Parse and import a single shipping Excel file using the provided session.

    Returns a summary dict for ShippingImportFile.summary.
    """
    xls = pd.ExcelFile(file_path, engine="calamine")

    user_lookup = ss.build_user_lookup(session)
    from app.models.build.config_number import ConfigNumber

    config_cache: dict = {
        cn.value: cn for cn in session.query(ConfigNumber).all()
    }

    stats = {"inserted": 0, "skipped_duplicate": 0, "missing_user": 0}
    missing_recipients: dict[str, str] = {}
    sheets_processed = 0
    sheets_skipped: list[str] = []

    # Pre-load sheets so we can compute a total before processing.
    loaded: list[tuple[str, pd.DataFrame]] = []
    total_rows = 0
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
        loaded.append((sheet_name, df))
        detected = ss.detect_header(df)
        if detected is None:
            continue
        header_row, col_map = detected
        config_idx = col_map.get("config")
        if config_idx is None:
            continue
        data = df.iloc[header_row + 1 :]
        for _, row in data.iterrows():
            if config_idx < len(row) and ss.clean(row.iloc[config_idx]) is not None:
                total_rows += 1

    if progress_cb:
        progress_cb("init", {"total": total_rows})

    for sheet_name, df in loaded:
        detected = ss.detect_header(df)
        if detected is None:
            sheets_skipped.append(sheet_name)
            if progress_cb:
                progress_cb(
                    "sheet_skipped",
                    {"sheet": sheet_name, "reason": "no_header"},
                )
            continue

        header_row, col_map = detected
        data = df.iloc[header_row + 1 :].copy()

        def cell(row, token):
            idx = col_map.get(token)
            if idx is None or idx >= len(row):
                return None
            return row.iloc[idx]

        sheet_inserted = 0
        for _, row in data.iterrows():
            raw_config = cell(row, "config")
            if ss.clean(raw_config) is None:
                continue

            from sqlalchemy import and_
            from app.models.order.shipping import Shipping
            from app.models.auth.user import User

            config_obj, _config_value = ss.get_or_create_config_number(
                session, config_cache, raw_config
            )
            if config_obj is None:
                continue

            ship_to_raw = cell(row, "ship_to")
            user = ss.find_user(user_lookup, ship_to_raw)

            # If the ship_to name does not match an existing user, auto-create
            # an INACTIVE placeholder user so the Shipments tab can still show
            # the handler/recipient name. PMs can later complete the user
            # record. This mirrors the behaviour of ``seed_shipments.py``.
            if user is None:
                cleaned_name = ss.sanitize_user_name(ship_to_raw)
                if cleaned_name:
                    user = User(
                        full_name=cleaned_name,
                        is_active=False,
                        can_login=False,
                    )
                    session.add(user)
                    session.flush()
                    for key in ss._name_keys(cleaned_name):
                        user_lookup.setdefault(key, user)

            # The shipped-to user IS the package recipient / handler under
            # the new schema (single column).
            recipient_user_id = user.id if user is not None else None

            if user is None:
                stats["missing_user"] += 1
                cleaned_name = ss.clean(ship_to_raw) or ""
                if cleaned_name:
                    keys = ss._name_keys(cleaned_name)
                    canonical = keys[0] if keys else cleaned_name.lower()
                    existing_display = missing_recipients.get(canonical)
                    if existing_display is None or len(cleaned_name) > len(
                        existing_display
                    ):
                        missing_recipients[canonical] = cleaned_name

            ship_date = ss.parse_date(cell(row, "ship_date"))
            eta = ss.parse_date(cell(row, "eta"))
            raw_delivery = cell(row, "delivery")
            delivery_date = ss.parse_date(raw_delivery)

            tracking = ss.clean_tracking(cell(row, "tracking"))
            forwarder_name = ss.clean(cell(row, "forwarder"))
            forwarder_id = ss.get_or_create_forwarder_id(session, forwarder_name)
            comments = ss.clean(cell(row, "comments"))
            quantity = ss.parse_quantity(cell(row, "quantity"))

            status = ss.infer_status(
                ship_date, delivery_date, ss.clean(raw_delivery)
            )

            existing = (
                session.query(Shipping)
                .filter(
                    and_(
                        Shipping.config_number_id == config_obj.id,
                        Shipping.recipient_user_id == recipient_user_id,
                        Shipping.ship_date == ship_date,
                        Shipping.tracking_number == tracking,
                    )
                )
                .first()
            )

            if existing:
                stats["skipped_duplicate"] += 1
                if progress_cb:
                    progress_cb(
                        "row_skipped",
                        {
                            "reason": "duplicate",
                            "config_number": config_obj.value,
                            "tracking": tracking,
                        },
                    )
                continue

            shipment = Shipping(
                config_number_id=config_obj.id,
                recipient_user_id=recipient_user_id,
                tracking_number=tracking,
                forwarder_id=forwarder_id,
                quantity=quantity,
                comments=comments,
                ship_date=ship_date,
                eta=eta,
                delivery_date=delivery_date,
                status=status,
            )
            session.add(shipment)
            stats["inserted"] += 1
            sheet_inserted += 1
            if progress_cb:
                progress_cb(
                    "row_done",
                    {
                        "config_number": config_obj.value,
                        "tracking": tracking,
                        "sheet": sheet_name,
                    },
                )

        session.flush()
        sheets_processed += 1

    return {
        "sheets_processed": sheets_processed,
        "sheets_skipped": sheets_skipped,
        "inserted": stats["inserted"],
        "skipped_duplicate": stats["skipped_duplicate"],
        "missing_user": stats["missing_user"],
        "missing_recipients": sorted(
            missing_recipients.values(), key=lambda n: n.lower()
        ),
        "total_rows": total_rows,
    }


def process_import_file(
    session: Session,
    import_file: ShippingImportFile,
    progress_cb: Callable[[str, dict[str, Any]], None] | None = None,
) -> ShippingImportFile:
    """Main entry point. Parses ``import_file`` and updates its status.

    On success the session is committed. On failure it is rolled back and the
    import_file row is re-fetched + flipped to ``failed`` in a fresh
    transaction so the error stays persisted.
    """
    # Bulk imports are excluded from `audit_logs` by design (see
    # db/bulk_import_pseudocode.md); mark the session so the audit
    # listeners skip every row written by this pipeline.
    session.info["skip_audit"] = True

    file_path = Path(import_file.storage_path)
    if not file_path.exists():
        import_file.status = ShippingImportStatus.failed
        import_file.error_message = f"File not found on disk: {file_path}"
        import_file.processed_at = datetime.now(timezone.utc)
        session.commit()
        return import_file

    import_file.status = ShippingImportStatus.processing
    import_file.error_message = None
    session.commit()

    try:
        summary = _process_file(session, file_path, progress_cb=progress_cb)
        import_file.status = ShippingImportStatus.success
        import_file.summary = summary
        import_file.processed_at = datetime.now(timezone.utc)
        session.commit()
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        # Re-fetch the row in a fresh transaction and mark it failed.
        fresh = (
            session.query(ShippingImportFile)
            .filter(ShippingImportFile.id == import_file.id)
            .first()
        )
        if fresh is not None:
            fresh.status = ShippingImportStatus.failed
            fresh.error_message = f"{type(exc).__name__}: {exc}"
            fresh.processed_at = datetime.now(timezone.utc)
            session.commit()
            # Refresh caller's reference
            import_file.status = fresh.status
            import_file.error_message = fresh.error_message
            import_file.processed_at = fresh.processed_at

    return import_file
