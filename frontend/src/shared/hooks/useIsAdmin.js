import { useAuthStore } from "@/shared/store/useAuthStore";

/**
 * Returns true if the currently authenticated user has the "Admin" role.
 * Supports both shapes the auth store may carry: a single `role` string or
 * a `roles` array (possibly of objects `{ role_name }` or plain strings).
 */
export function useIsAdmin() {
  const user = useAuthStore((s) => s.user);
  if (!user) return false;
  if (user.role === "Admin") return true;
  const rs = user.roles;
  if (!Array.isArray(rs)) return false;
  return rs.some((r) => {
    if (typeof r === "string") return r === "Admin";
    return r?.role_name === "Admin";
  });
}
