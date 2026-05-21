from app.models.auth.user import User


class RBACService:
    @staticmethod
    def get_user_permissions(user: User) -> set[str]:
        return {
            permission.code
            for role in user.roles
            for permission in role.permissions
        }

    @staticmethod
    def get_user_roles(user: User) -> set[str]:
        return {role.role_name for role in user.roles}

    @staticmethod
    def has_permission(
        user_permissions: set[str],
        required_permission: str,
    ) -> bool:
        """
        Supports:
        - exact permission: user:read
        - module wildcard: user:*
        - global wildcard: *
        """

        if "*" in user_permissions:
            return True

        if required_permission in user_permissions:
            return True

        module = required_permission.split(":")[0]
        module_wildcard = f"{module}:*"

        if module_wildcard in user_permissions:
            return True

        return False

    @staticmethod
    def has_any_permission(
        user_permissions: set[str],
        required_permissions: list[str],
    ) -> bool:
        return any(
            RBACService.has_permission(user_permissions, permission)
            for permission in required_permissions
        )

    @staticmethod
    def has_all_permissions(
        user_permissions: set[str],
        required_permissions: list[str],
    ) -> bool:
        return all(
            RBACService.has_permission(user_permissions, permission)
            for permission in required_permissions
        )