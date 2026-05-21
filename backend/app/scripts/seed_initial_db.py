from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.auth.user import User
from app.models.auth.role import Role
from app.models.auth.user_role import UserRole
from app.models.auth.department import Department
from app.models.build.family import Family
from app.models.build.form_factor import FormFactor
from app.models.build.pm_family import PMFamily
from app.core.security import hash_password
from app.scripts.seed_build_plan import seed_default_warehouses


EXCEL_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "NPI-DBMS_UserList.xlsx"
)


def clean_text(value):
    if pd.isna(value):
        return None

    # Fix Excel numeric values like 12282943.0 -> "12282943"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    value = str(value).strip()

    if value == "":
        return None

    # Extra safety: fix string values like "12282943.0"
    if value.endswith(".0") and value[:-2].isdigit():
        return value[:-2]

    return value


def split_csv(value):
    """Split a comma-separated cell value into a list of trimmed tokens.

    Returns an empty list when the value is empty/None.
    """
    cleaned = clean_text(value)
    if not cleaned:
        return []
    return [token.strip() for token in cleaned.split(",") if token.strip()]


def _find_column(df: pd.DataFrame, *candidates: str):
    """Return the first column whose normalized name matches a candidate.

    Case-insensitive; ignores surrounding whitespace.
    """
    normalized = {str(c).strip().lower(): c for c in df.columns}
    for cand in candidates:
        col = normalized.get(cand.strip().lower())
        if col is not None:
            return col
    return None


def get_or_create_department(db: Session, name: str):
    if not name:
        return None

    department = (
        db.query(Department)
        .filter(Department.name == name)
        .first()
    )

    if department:
        return department

    department = Department(name=name)
    db.add(department)
    db.flush()

    return department


def get_or_create_role(db: Session, role_name: str):
    if not role_name:
        return None

    role = (
        db.query(Role)
        .filter(Role.role_name == role_name)
        .first()
    )

    if role:
        return role

    role = Role(role_name=role_name)
    db.add(role)
    db.flush()

    return role


def seed_departments(db: Session, excel_file: Path):
    df = pd.read_excel(excel_file, engine='calamine', sheet_name="Department List")

    created = 0
    skipped = 0

    for _, row in df.iterrows():
        department_name = clean_text(row.get("Departments"))

        if not department_name:
            skipped += 1
            continue

        existing = (
            db.query(Department)
            .filter(Department.name == department_name)
            .first()
        )

        if existing:
            skipped += 1
            continue

        db.add(Department(name=department_name))
        created += 1

    db.flush()

    print(f"Departments → Created: {created}, Skipped existing/empty: {skipped}")


def seed_roles(db: Session, excel_file: Path):
    df = pd.read_excel(excel_file, engine='calamine', sheet_name="Role List")

    created = 0
    skipped = 0

    for _, row in df.iterrows():
        role_name = clean_text(row.get("Roles"))

        if not role_name:
            skipped += 1
            continue

        existing = (
            db.query(Role)
            .filter(Role.role_name == role_name)
            .first()
        )

        if existing:
            skipped += 1
            continue

        db.add(Role(role_name=role_name))
        created += 1

    db.flush()

    print(f"Roles → Created: {created}, Skipped existing/empty: {skipped}")


def seed_families(db: Session, excel_file: Path):
    """Upsert Family rows from the "Family" sheet.

    Expected columns (case-insensitive): ``Code`` and ``Name`` (also accepts
    ``Nam`` as a typo-tolerant fallback).
    """
    try:
        df = pd.read_excel(excel_file, engine="calamine", sheet_name="Family")
    except ValueError as exc:
        print(f"[WARN] Family sheet not found, skipping: {exc}")
        return

    code_col = _find_column(df, "Code")
    name_col = _find_column(df, "Name", "Nam")

    if code_col is None:
        print("[WARN] Family sheet missing 'Code' column; skipping.")
        return

    created = 0
    updated = 0
    skipped = 0

    for _, row in df.iterrows():
        code = clean_text(row.get(code_col))
        name = clean_text(row.get(name_col)) if name_col else None

        if not code:
            skipped += 1
            continue

        if not name:
            name = code  # fallback: use code as name when missing

        family = db.query(Family).filter(Family.code == code).first()

        if family:
            # Backfill name only when current name is a placeholder (== code).
            if family.name == family.code and name and name != family.name:
                family.name = name
                updated += 1
                print(f"[FAMILY UPDATE] {code} → name='{name}'")
            else:
                skipped += 1
            continue

        db.add(Family(code=code, name=name))
        created += 1
        print(f"[FAMILY CREATE] {code} → {name}")

    db.flush()

    print(
        f"Families → Created: {created}, Updated: {updated}, "
        f"Skipped existing/empty: {skipped}"
    )


def seed_form_factors(db: Session, excel_file: Path):
    """Upsert FormFactor rows from the "Form Factor" sheet.

    Expected column (case-insensitive): ``Name``. Each row's name is upserted
    as a canonical FormFactor row.
    """
    try:
        df = pd.read_excel(excel_file, engine="calamine", sheet_name="Form Factor")
    except ValueError as exc:
        print(f"[WARN] Form Factor sheet not found, skipping: {exc}")
        return

    name_col = _find_column(df, "Name")

    if name_col is None:
        print("[WARN] Form Factor sheet missing 'Name' column; skipping.")
        return

    created = 0
    skipped = 0

    for _, row in df.iterrows():
        name = clean_text(row.get(name_col))

        if not name:
            skipped += 1
            continue

        existing = (
            db.query(FormFactor)
            .filter(FormFactor.name == name)
            .first()
        )

        if existing:
            skipped += 1
            continue

        db.add(FormFactor(name=name))
        created += 1
        print(f"[FORM-FACTOR CREATE] {name}")

    db.flush()

    print(
        f"Form Factors → Created: {created}, Skipped existing/empty: {skipped}"
    )


def assign_role_to_user(db: Session, user: User, role: Role):
    if not user or not role:
        return False

    existing_user_role = (
        db.query(UserRole)
        .filter(
            UserRole.user_id == user.id,
            UserRole.role_id == role.id,
        )
        .first()
    )

    if existing_user_role:
        return False

    db.add(
        UserRole(
            user_id=user.id,
            role_id=role.id,
        )
    )

    return True


def link_pm_family(db: Session, user: User, family: Family) -> str:
    """Create a PMFamily ownership row.

    Enforces the rule that a family can only be owned by one PM. Returns:
      - "created"  : new ownership row inserted
      - "exists"   : this user already owns this family
      - "conflict" : a different user already owns this family (skipped)
    """
    if not user or not family:
        return "skipped"

    existing_for_user = (
        db.query(PMFamily)
        .filter(
            PMFamily.user_id == user.id,
            PMFamily.family_id == family.id,
        )
        .first()
    )

    if existing_for_user:
        return "exists"

    other_owner = (
        db.query(PMFamily)
        .filter(PMFamily.family_id == family.id)
        .first()
    )

    if other_owner:
        return "conflict"

    db.add(PMFamily(user_id=user.id, family_id=family.id))
    return "created"


def seed_users(db: Session, excel_file: Path):
    df = pd.read_excel(excel_file, engine='calamine', sheet_name="User List")

    role_col = _find_column(df, "Roles", "Role", "ROLE", "ROLES")
    family_col = _find_column(df, "Family", "Families")

    created = 0
    updated = 0
    skipped = 0
    roles_assigned = 0
    pm_families_linked = 0
    pm_family_conflicts = 0
    pm_family_missing = 0

    for index, row in df.iterrows():
        row_number = index + 2  # Excel header is row 1

        full_name = clean_text(row.get("NAME"))
        employee_id = clean_text(row.get("WWID"))
        email = clean_text(row.get("EMAIL"))
        password = clean_text(row.get("PASSWORD"))
        department_name = clean_text(row.get("DEPARTMENT"))

        role_tokens = split_csv(row.get(role_col)) if role_col else []
        family_codes = split_csv(row.get(family_col)) if family_col else []

        department = get_or_create_department(db, department_name)

        query = db.query(User)

        user = None

        if email:
            user = query.filter(User.email == email).first()

        if not user and employee_id:
            user = query.filter(User.employee_id == employee_id).first()

        if not user and full_name:
            user = query.filter(
                User.full_name == full_name,
                User.email.is_(None),
                User.employee_id.is_(None),
            ).first()

        if not user:
            has_login = bool(email and password)
            password_hash = hash_password(password) if has_login else None

            user = User(
                employee_id=employee_id if employee_id else None,
                email=email if email else None,
                full_name=full_name,
                password_hash=password_hash,
                department_id=department.id if department else None,
                is_active=has_login,
                can_login=has_login,
                legacy_ref = f"excel-user-row-{row_number}"
            )

            db.add(user)
            db.flush()

            created += 1
            print(f"[CREATE] {email}")

        else:
            has_login = bool(email and password)

            user.employee_id = employee_id if employee_id else None
            user.email = email if email else None
            user.full_name = full_name
            user.department_id = department.id if department else None
            user.is_active = has_login
            user.can_login = has_login

            if has_login and not user.password_hash:
                user.password_hash = hash_password(password)

            # Keep existing password by default.
            # Uncomment below only if you want Excel password to overwrite DB password.
            #
            # try:
            #     user.password_hash = hash_password(password)
            # except Exception as e:
            #     skipped += 1
            #     print(f"[SKIP PASSWORD UPDATE row {row_number}] {email}: {e}")

            updated += 1
            print(f"[UPDATE] {email}")

        # ------------------------------------------------------------------
        # Roles: one row per comma-separated token in the Roles/ROLE column.
        # ------------------------------------------------------------------
        for token in role_tokens:
            role = get_or_create_role(db, token)
            if not role:
                continue
            if assign_role_to_user(db, user, role):
                roles_assigned += 1
                print(f"[ROLE] Assigned {role.role_name} to {email}")

        # ------------------------------------------------------------------
        # PM-Family ownership: one pm_families row per family code listed.
        # Only valid for users that include "Program Manager" or "Admin"
        # in their roles for this row.
        # ------------------------------------------------------------------
        if family_codes:
            normalized_roles = {t.strip().lower() for t in role_tokens}
            is_pm_or_admin = (
                "program manager" in normalized_roles
                or "admin" in normalized_roles
            )

            if not is_pm_or_admin:
                print(
                    f"[WARN row {row_number}] Skipping family links for "
                    f"{email or full_name}: not a Program Manager/Admin "
                    f"(roles={role_tokens})"
                )
            else:
                for code in family_codes:
                    family = (
                        db.query(Family)
                        .filter(Family.code == code)
                        .first()
                    )

                    if not family:
                        pm_family_missing += 1
                        print(
                            f"[WARN row {row_number}] Family code not found: "
                            f"{code} (referenced by {email or full_name})"
                        )
                        continue

                    result = link_pm_family(db, user, family)

                    if result == "created":
                        pm_families_linked += 1
                        print(
                            f"[PM-FAMILY] {email or full_name} → {code} "
                            f"({family.name})"
                        )
                    elif result == "conflict":
                        pm_family_conflicts += 1
                        print(
                            f"[WARN row {row_number}] Family {code} already "
                            f"owned by another PM; skipping link to "
                            f"{email or full_name}"
                        )

    print(
        f"Users → Created: {created}, Updated: {updated}, "
        f"Skipped: {skipped}, Roles assigned: {roles_assigned}, "
        f"PM-Family links: {pm_families_linked}, "
        f"Family conflicts: {pm_family_conflicts}, "
        f"Missing family codes: {pm_family_missing}"
    )


def _find_user_by_name(db: Session, full_name: str):
    if not full_name:
        return None

    return (
        db.query(User)
        .filter(User.full_name.ilike(full_name.strip()))
        .first()
    )


def main():
    print(f"Reading Excel from: {EXCEL_FILE}")

    if not EXCEL_FILE.exists():
        raise FileNotFoundError(f"Excel file not found: {EXCEL_FILE}")

    db = SessionLocal()

    try:
        seed_departments(db, EXCEL_FILE)
        seed_roles(db, EXCEL_FILE)
        seed_families(db, EXCEL_FILE)
        seed_form_factors(db, EXCEL_FILE)
        seed_users(db, EXCEL_FILE)
        seed_default_warehouses(db)

        db.commit()

        print("User data import completed successfully.")

    except Exception as e:
        db.rollback()
        print("Import failed. Database rollback completed.")
        raise e

    finally:
        db.close()


if __name__ == "__main__":
    main()