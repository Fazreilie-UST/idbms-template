# app/scripts/seed_shipments.py
"""
Seed shipment records from `backend/data/Master Board Tracker.xlsx`.

Each sheet (one per family product, e.g. GfP/TyP, JnP, GaP...) follows the
same layout:

    Row 0  -> sheet title
    Row 1  -> blank
    Row 2  -> headers: [_, No, Ship Date, Config Number, Quantity,
                        Ship To, Forwarder, Tracking Number, ETA,
                        Delivery Date, Comments]
    Row 3+ -> data

For every row we:
1. Resolve / create a ConfigNumber by the raw `Config Number` value.
   Shipments are linked to ConfigNumber, not BuildPlan, so a shipment
   can be loaded even if its BuildPlan has not been imported yet.
   Whenever a BuildPlan with the same config_number is later created,
   it will automatically share the link via ConfigNumber.
2. Resolve `Ship To` -> User by `full_name` (optional).
3. Set `recipient_user_id` directly to that user. This single column
   represents the "Handler" (the user the package physically ships to);
   the legacy `handler_id` column has been merged into `recipient_user_id`.
4. Insert the shipment, dedupe by
   (config_number_id, recipient_user_id, ship_date, tracking_number).
   Unknown `Ship To` names are written to
   `data/_seed_shipments_missing_recipients.json` as a JSON array.

Run from the `backend/` directory:

    python -m app.scripts.seed_shipments
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.db.session import SessionLocal

from app.models.auth.user import User
from app.models.build.config_number import ConfigNumber
from app.models.order.forwarder import Forwarder
from app.models.order.shipping import Shipping, ShippingStatus

# For explicit audit logging
from app.services.audit_service import AuditService
from app.models.audit.audit_log import AuditModule, AuditAction


EXCEL_PATH = Path(
    "/home/fbinalex/NPI-IDBMS/backend/data/Master Board Tracker.xlsx"
)

MISSING_RECIPIENTS_LOG = Path(
    "/home/fbinalex/NPI-IDBMS/backend/data/_seed_shipments_missing_recipients.json"
)

# Header tokens we expect to see in the column header row.
HEADER_TOKENS = {
    "no": "no",
    "ship date": "ship_date",
    "config number": "config",
    "quantity": "quantity",
    "ship to": "ship_to",
    "forwarder": "forwarder",
    "tracking number": "tracking",
    "eta": "eta",
    "delivery date": "delivery",
    "delivery\ndate": "delivery",
    "comments": "comments",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def clean(value):
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.lower() in {"nan", "<na>", "none", "null", "nat"}:
        return None
    return text


def clean_config(value):
    value = clean(value)
    if not value:
        return None
    # Normalise internal whitespace
    return re.sub(r"\s+", " ", value).strip()


# Strip parenthesised annotations + trailing warehouse-stash noise so users
# auto-created from this sheet keep a clean ``full_name``.
_PARENS_RE = re.compile(r"\([^)]*\)")
_TRAILING_NOISE_RE = re.compile(
    r"\s*[-–—]\s*(?:to\s+)?(?:keep\s+for\s+test|solder\s+down(?:\s+only)?)\s*$",
    re.IGNORECASE,
)


def sanitize_user_name(raw) -> str | None:
    cleaned = clean(raw)
    if not cleaned:
        return None
    text = _PARENS_RE.sub("", cleaned)
    while True:
        new_text = _TRAILING_NOISE_RE.sub("", text)
        if new_text == text:
            break
        text = new_text
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


def clean_tracking(value):
    value = clean(value)
    if not value:
        return None
    return value.replace("\n", "").replace("\r", "").strip()


def parse_date(value):
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = clean(value)
    if not text:
        return None
    # Some cells contain status strings like "Delivered" instead of a date
    try:
        return pd.to_datetime(text, errors="raise").date()
    except (ValueError, TypeError):
        return None


def parse_quantity(value):
    text = clean(value)
    if text is None:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------

def _name_keys(full_name: str) -> list[str]:
    """Generate normalised lookup keys for a person's name."""
    if not full_name:
        return []
    base = re.sub(r"\s+", " ", full_name).strip().lower()
    if not base:
        return []
    keys = {base}
    # Strip all punctuation/whitespace
    compact = re.sub(r"[\s,.\-]+", "", base)
    keys.add(compact)
    # Token-set signature (handles "Last, First" vs "First Last")
    tokens = sorted(t for t in re.split(r"[\s,]+", base) if t)
    if tokens:
        keys.add("|".join(tokens))
    return [k for k in keys if k]


def build_user_lookup(session: Session) -> dict[str, User]:
    """Map several normalised name variants -> User."""
    lookup: dict[str, User] = {}
    for user in session.query(User).all():
        if not user.full_name:
            continue
        for key in _name_keys(user.full_name):
            lookup.setdefault(key, user)
    return lookup


def build_buildplan_lookup(session: Session) -> None:
    """Deprecated; kept as a no-op for backwards compatibility."""
    return None


def get_or_create_config_number(
    session: Session,
    cache: dict[str, ConfigNumber],
    raw_config: str,
) -> tuple[ConfigNumber | None, str | None]:
    config = clean_config(raw_config)
    if not config:
        return None, None

    cached = cache.get(config)
    if cached is not None:
        return cached, config

    # Try existing (case-sensitive then insensitive fallback)
    existing = (
        session.query(ConfigNumber)
        .filter(ConfigNumber.value == config)
        .first()
    )
    if existing is None:
        compact = config.replace(" ", "")
        for stored_value, cn in cache.items():
            if stored_value.replace(" ", "") == compact:
                existing = cn
                break
    if existing is None:
        existing = ConfigNumber(value=config)
        session.add(existing)
        session.flush()
    cache[config] = existing
    return existing, config


def find_user(
    user_lookup: dict[str, User],
    raw_name: str,
) -> User | None:
    name = clean(raw_name)
    if not name:
        return None
    for key in _name_keys(name):
        user = user_lookup.get(key)
        if user:
            return user
    return None


_forwarder_cache: dict[str, int] = {}


def get_or_create_forwarder_id(session: Session, raw_name: str | None) -> int | None:
    name = clean(raw_name)
    if not name:
        return None
    key = name.lower()
    cached = _forwarder_cache.get(key)
    if cached is not None:
        return cached
    existing = (
        session.query(Forwarder)
        .filter(Forwarder.name.ilike(name))
        .first()
    )
    if existing is None:
        existing = Forwarder(name=name)
        session.add(existing)
        session.flush()
    _forwarder_cache[key] = existing.id
    return existing.id


# ---------------------------------------------------------------------------
# Status inference
# ---------------------------------------------------------------------------

def infer_status(
    ship_date: date | None,
    delivery_date: date | None,
    raw_delivery_text: str | None,
) -> ShippingStatus:
    if delivery_date is not None:
        return ShippingStatus.completed
    text = (raw_delivery_text or "").strip().lower()
    if text in {"delivered", "completed"}:
        return ShippingStatus.completed
    if ship_date is not None:
        return ShippingStatus.shipped_out
    return ShippingStatus.scheduled


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

def detect_header(sheet_df: pd.DataFrame) -> tuple[int, dict[str, int]] | None:
    """Find the row containing the column headers and return its index +
    a mapping of token -> column index."""
    max_scan = min(10, sheet_df.shape[0])
    for row_idx in range(max_scan):
        row = sheet_df.iloc[row_idx]
        col_map: dict[str, int] = {}
        for col_idx, raw in enumerate(row):
            if raw is None or (isinstance(raw, float) and pd.isna(raw)):
                continue
            key = str(raw).strip().lower().replace("\n", " ")
            key = re.sub(r"\s+", " ", key)
            token = HEADER_TOKENS.get(key)
            if token and token not in col_map:
                col_map[token] = col_idx
        # Require these to confidently call it a header row
        required = {"config", "ship_to", "tracking", "quantity"}
        if required.issubset(col_map.keys()):
            return row_idx, col_map
    return None


def seed_sheet(
    session: Session,
    sheet_df: pd.DataFrame,
    sheet_name: str,
    user_lookup: dict[str, User],
    config_cache: dict[str, ConfigNumber],
    stats: dict[str, int],
    missing_recipients: dict[str, str],
) -> None:
    detected = detect_header(sheet_df)
    if detected is None:
        print(f"[{sheet_name}] No header row detected -- skipping sheet")
        return

    header_row, col_map = detected
    data = sheet_df.iloc[header_row + 1 :].copy()

    def cell(row, token):
        idx = col_map.get(token)
        if idx is None or idx >= len(row):
            return None
        return row.iloc[idx]

    for _, row in data.iterrows():
        raw_config = cell(row, "config")
        if clean(raw_config) is None:
            continue

        config_obj, config_value = get_or_create_config_number(
            session, config_cache, raw_config
        )
        if config_obj is None:
            continue

        ship_to_raw = cell(row, "ship_to")
        user = find_user(user_lookup, ship_to_raw)

        # If the recipient name from the shipment file does not match any
        # existing user, auto-create a placeholder user so the shipment row
        # still gets a `recipient_user_id`.
        if user is None:
            cleaned_name = sanitize_user_name(ship_to_raw)
            if cleaned_name:
                user = User(
                    full_name=cleaned_name,
                    is_active=False,
                    can_login=False,
                )
                session.add(user)
                session.flush()
                for key in _name_keys(cleaned_name):
                    user_lookup.setdefault(key, user)
                stats["users_created"] = stats.get("users_created", 0) + 1

        # The shipped-to user IS the package recipient / handler under the
        # new schema (single column).
        recipient_user_id = user.id if user is not None else None

        if user is None:
            stats["missing_user"] += 1
            cleaned_name = clean(ship_to_raw) or ""
            if not cleaned_name:
                continue
            keys = _name_keys(cleaned_name)
            canonical = keys[0] if keys else cleaned_name.lower()
            existing_display = missing_recipients.get(canonical)
            if existing_display is None or len(cleaned_name) > len(existing_display):
                missing_recipients[canonical] = cleaned_name

        ship_date = parse_date(cell(row, "ship_date"))
        eta = parse_date(cell(row, "eta"))
        raw_delivery = cell(row, "delivery")
        delivery_date = parse_date(raw_delivery)

        tracking = clean_tracking(cell(row, "tracking"))
        forwarder_name = clean(cell(row, "forwarder"))
        forwarder_id = get_or_create_forwarder_id(session, forwarder_name)
        comments = clean(cell(row, "comments"))
        quantity = parse_quantity(cell(row, "quantity"))

        status = infer_status(ship_date, delivery_date, clean(raw_delivery))

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


def seed_shipments(file_path: Path = EXCEL_PATH) -> None:
    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")

    xls = pd.ExcelFile(file_path)

    with SessionLocal() as session:
        try:
            user_lookup = build_user_lookup(session)
            config_cache: dict[str, ConfigNumber] = {
                cn.value: cn for cn in session.query(ConfigNumber).all()
            }

            stats = {
                "inserted": 0,
                "skipped_duplicate": 0,
                "missing_user": 0,
            }
            missing_recipients: dict[str, str] = {}

            for sheet_name in xls.sheet_names:
                print(f"=== Processing sheet: {sheet_name} ===")
                df = pd.read_excel(xls, engine='calamine', sheet_name=sheet_name, header=None)
                seed_sheet(
                    session=session,
                    sheet_df=df,
                    sheet_name=sheet_name,
                    user_lookup=user_lookup,
                    config_cache=config_cache,
                    stats=stats,
                    missing_recipients=missing_recipients,
                )
                session.flush()

            session.commit()

            print("\nShipment seeding complete:")
            for key, value in stats.items():
                print(f"  {key}: {value}")

            if missing_recipients:
                MISSING_RECIPIENTS_LOG.parent.mkdir(parents=True, exist_ok=True)
                names = sorted(
                    missing_recipients.values(),
                    key=lambda n: n.lower(),
                )
                with MISSING_RECIPIENTS_LOG.open("w", encoding="utf-8") as fh:
                    json.dump(names, fh, ensure_ascii=False, indent=2)
                    fh.write("\n")
                print(
                    f"  unique missing recipients: {len(missing_recipients)} "
                    f"(see {MISSING_RECIPIENTS_LOG})"
                )

        except Exception:
            session.rollback()
            print("Shipment seeding failed. Rolled back.")
            raise


if __name__ == "__main__":
    seed_shipments()

    # --- Explicit Audit Log Entry ---
    # This assumes the import was successful and at least one shipment was imported.
    # If you want to log each shipment, move this logic inside the import loop.
    from app.db.session import SessionLocal
    with SessionLocal() as session:
        AuditService.record(
            session,
            module=AuditModule.shipping,
            action=AuditAction.create,
            record_id=0,  # 0 or -1 for bulk/system import; or use a real shipment.id if available
            user_id=1,    # Use 1 or a system user if unknown
            new_value={"file": str(EXCEL_PATH), "event": "Bulk shipment import"},
        )
        session.commit()
