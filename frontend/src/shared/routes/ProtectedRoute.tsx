import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore, type AuthUser } from "@/shared/store/useAuthStore";

interface ProtectedRouteProps {
  allowedRoles?: string[];
}

function ProtectedRoute({ allowedRoles = [] }: ProtectedRouteProps) {
  const { user } = useAuthStore();

  let storedUser: AuthUser | null = user;
  if (!storedUser) {
    try {
      const raw = localStorage.getItem("user");
      storedUser = raw ? (JSON.parse(raw) as AuthUser) : null;
    } catch {
      storedUser = null;
    }
  }
  const storedRole = (() => {
    try {
      return localStorage.getItem("role");
    } catch {
      return null;
    }
  })();

  // Resolve role from any available source: explicit `role`, `roles[0]` array
  // (as returned by the backend), or the persisted role in localStorage.
  const resolvedRole: string | null =
    storedUser?.role ||
    (Array.isArray(storedUser?.roles) ? storedUser.roles[0] : null) ||
    storedRole ||
    null;

  // Auth lives in httpOnly cookies; the presence of a `user`/role in
  // localStorage is our local hint. If a request later returns 401 the
  // global handler in helper.ts will clear `user` and bounce to "/".
  const resolvedUser: AuthUser | null =
    storedUser ?? (resolvedRole ? ({ role: resolvedRole } satisfies AuthUser) : null);

  if (!resolvedUser) {
    return <Navigate to="/" replace />;
  }

  // Admin has the union of all role permissions; treat the Admin role as a
  // member of every `allowedRoles` set so admins can access PM and Requestor
  // pages without separate route definitions.
  const hasAccess =
    allowedRoles.length === 0 ||
    (resolvedRole != null &&
      (resolvedRole === "Admin" || allowedRoles.includes(resolvedRole)));

  if (!hasAccess) {
    if (resolvedRole === "Program Manager") {
      return <Navigate to="/pm/dashboard" replace />;
    }

    if (resolvedRole === "Requestor") {
      return <Navigate to="/requestor/dashboard" replace />;
    }

    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}

export default ProtectedRoute;
