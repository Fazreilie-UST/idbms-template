from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.auth.role import Role
from app.models.auth.permission import Permission
from app.models.auth.role_permission import RolePermission
from app.models.auth.action_category import ActionCategory


ACTION_CATEGORIES = [
    "users",
    "roles",
    "permissions",
    "build_plans",
    "build_requests",
    "shipping",
    "stock",
    "pm_families",
]


PERMISSIONS = [
    # Users
    ("user:manage", "Manage Users", "Create, update, activate, deactivate users", "users"),
    ("user:read", "Read Users", "View user data", "users"),

    # Roles
    ("role:manage", "Manage Roles", "Create, update, delete roles", "roles"),
    ("role:read", "Read Roles", "View roles", "roles"),

    # Permissions
    ("permission:manage", "Manage Permissions", "Create and update permissions", "permissions"),
    ("permission:read", "Read Permissions", "View permissions", "permissions"),

    # Build Plans
    ("build_plan:create", "Create Build Plan", "Create build plans", "build_plans"),
    ("build_plan:read", "Read Build Plan", "View build plans", "build_plans"),
    ("build_plan:update", "Update Build Plan", "Update build plans", "build_plans"),
    ("build_plan:send", "Send Build Plan", "Send build plan to ODM", "build_plans"),
    ("build_plan:lock", "Lock Build Plan", "Lock build plan", "build_plans"),
    ("build_plan:revise", "Revise Build Plan", "Revise build plan", "build_plans"),
    ("build_plan:import", "Import Build Plan", "Bulk import historical build plan files", "build_plans"),

    # Build Requests
    ("build_request:create", "Create Build Request", "Create build request", "build_requests"),
    ("build_request:read", "Read Build Request", "View build requests", "build_requests"),
    ("build_request:update", "Update Build Request", "Update build request", "build_requests"),
    ("build_request:approve", "Approve Build Request", "Approve build request", "build_requests"),
    ("build_request:cancel", "Cancel Build Request", "Cancel build request", "build_requests"),

    # Shipping
    ("shipping:create", "Create Shipping", "Create shipping records", "shipping"),
    ("shipping:read", "Read Shipping", "View shipping records", "shipping"),
    ("shipping:update", "Update Shipping", "Update shipping records", "shipping"),
    ("shipping:import", "Import Shipping", "Bulk import shipment files", "shipping"),

    ("user:*", "Manage All User Actions", "Full access to user module", "users"),
    ("build_plan:*", "Manage All Build Plan Actions", "Full access to build plans", "build_plans"),
    ("build_request:*", "Manage All Build Request Actions", "Full access to build requests module", "build_requests"),
    ("shipping:*", "Manage All Shipping Actions", "Full access to shipping module", "shipping"),

    # Stock
    ("stock:read", "Read Stock", "View stock data", "stock"),
    ("stock:import", "Import Stock", "Import stock data", "stock"),
    ("stock:delete", "Delete Stock", "Delete stock data", "stock"),

    # PM <-> Family assignments (admin-managed)
    ("pm_family:read", "Read PM-Family", "View PM-Family assignments", "pm_families"),
    ("pm_family:manage", "Manage PM-Family", "Create/delete PM-Family assignments (Admin only)", "pm_families"),
]


ROLES = [
    ("Admin", "Full system administrator"),
    ("Program Manager", "Manages build plans, users, requests, and shipping"),
    ("Requestor", "Creates and updates own build requests"),
    ("Coordinator", "Manages shipment updates"),
    ("ODM", "External manufacturing partner"),
    ("Normal User", "Basic read-only user"),
    ("None", "No access"),
]


ROLE_PERMISSIONS = {
    "Admin": [
        "*",
    ],

    "Program Manager": [
        "user:read",
        "role:read",
        "permission:read",
        "build_plan:*",
        "build_request:*",
        "shipping:*",
        "pm_family:read",
    ],

    "Requestor": [
        "build_plan:read",
        "build_request:create",
        "build_request:read",
        "build_request:update",
        "build_request:cancel",
        "shipping:read",
    ],

    "Normal User": [
        "build_plan:read",
        "build_request:read",
        "shipping:read"
    ],

    # "Coordinator": [
    #     "build_request:read",
    #     "shipping:create",
    #     "shipping:read",
    #     "shipping:update",
    # ],

    # "ODM": [
    #     "build_plan:read",
    #     "shipping:create",
    #     "shipping:read",
    #     "shipping:update",
    # ],
}


def get_or_create_category(db: Session, name: str) -> ActionCategory:
    category = (
        db.query(ActionCategory)
        .filter(ActionCategory.name == name)
        .first()
    )

    if category:
        return category

    category = ActionCategory(name=name)
    db.add(category)
    db.flush()

    return category


def get_or_create_role(db: Session, role_name: str, description: str | None = None) -> Role:
    role = db.query(Role).filter(Role.role_name == role_name).first()

    if role:
        role.description = description
        return role

    role = Role(role_name=role_name, description=description)
    db.add(role)
    db.flush()

    return role


def get_or_create_permission(
    db: Session,
    code: str,
    name: str,
    description: str,
    category: ActionCategory,
) -> Permission:
    permission = db.query(Permission).filter(Permission.code == code).first()

    if permission:
        permission.name = name
        permission.description = description
        permission.action_category_id = category.id
        return permission

    permission = Permission(
        code=code,
        name=name,
        description=description,
        action_category_id=category.id,
    )

    db.add(permission)
    db.flush()

    return permission


def assign_permission_to_role(db: Session, role: Role, permission: Permission) -> bool:
    existing = (
        db.query(RolePermission)
        .filter(
            RolePermission.role_id == role.id,
            RolePermission.permission_id == permission.id,
        )
        .first()
    )

    if existing:
        return False

    db.add(
        RolePermission(
            role_id=role.id,
            permission_id=permission.id,
        )
    )

    return True


def seed_rbac(db: Session):
    category_map = {}

    for category_name in ACTION_CATEGORIES:
        category_map[category_name] = get_or_create_category(db, category_name)

    role_map = {}

    for role_name, description in ROLES:
        role_map[role_name] = get_or_create_role(db, role_name, description)

    permission_map = {}

    for code, name, description, category_name in PERMISSIONS:
        permission_map[code] = get_or_create_permission(
            db=db,
            code=code,
            name=name,
            description=description,
            category=category_map[category_name],
        )

    assigned_count = 0
    skipped_count = 0

    all_permissions = list(permission_map.values())

    for role_name, permission_codes in ROLE_PERMISSIONS.items():
        role = role_map[role_name]

        if "*" in permission_codes:
            permissions_to_assign = all_permissions
        else:
            permissions_to_assign = [
                permission_map[code]
                for code in permission_codes
                if code in permission_map
            ]

        for permission in permissions_to_assign:
            assigned = assign_permission_to_role(db, role, permission)

            if assigned:
                assigned_count += 1
            else:
                skipped_count += 1

    print("RBAC seed completed.")
    print(f"Roles: {len(role_map)}")
    print(f"Permissions: {len(permission_map)}")
    print(f"Role permissions assigned: {assigned_count}")
    print(f"Role permissions skipped existing: {skipped_count}")


def main():
    db = SessionLocal()

    try:
        seed_rbac(db)
        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()