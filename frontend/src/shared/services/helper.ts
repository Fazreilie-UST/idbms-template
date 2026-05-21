// Use a module-level flag to avoid stacking multiple redirects/messages
// when many in-flight requests all fail with 401 at once.
let unauthorizedHandled = false;

const CSRF_COOKIE = "csrf_token";
const CSRF_HEADER = "X-CSRF-Token";

function isAuthEndpoint(url: string | undefined): boolean {
  if (!url) return false;
  return url.includes("/auth/login") || url.includes("/auth/refresh");
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(name + "="));
  if (!match) return null;
  try {
    return decodeURIComponent(match.slice(name.length + 1));
  } catch {
    return match.slice(name.length + 1);
  }
}

function forceLogout(reason: string): void {
  if (unauthorizedHandled) return;
  unauthorizedHandled = true;

  // Auth tokens live in httpOnly cookies (managed by the backend) so we don't
  // wipe them here. Only clear UI-state user info from localStorage.
  try {
    localStorage.removeItem("user");
    localStorage.removeItem("role");
  } catch {
    /* ignore storage errors */
  }

  // Notify the rest of the app (e.g. zustand store, layout) that auth is gone.
  try {
    window.dispatchEvent(
      new CustomEvent("auth:unauthorized", { detail: { reason } }),
    );
  } catch {
    /* ignore */
  }

  // Redirect to login (only if we're not already there)
  if (typeof window !== "undefined") {
    const here = window.location.pathname;
    if (here !== "/" && here !== "/login") {
      window.location.replace("/");
    }
  }
}

interface ErrorBody {
  detail?: string;
  message?: string;
  error?: { message?: string };
}

export async function handleResponse<T = unknown>(res: Response): Promise<T> {
  if (res.status === 401 && !isAuthEndpoint(res.url)) {
    let detail = "Session expired. Please sign in again.";
    try {
      const body = (await res.clone().json()) as ErrorBody;
      detail = body.detail || body.message || detail;
    } catch {
      /* ignore */
    }
    forceLogout(detail);
    throw new Error(detail);
  }

  if (!res.ok) {
    let messageText = "Request failed";
    try {
      const err = (await res.json()) as ErrorBody;
      messageText = err.detail || err.message || messageText;
    } catch {
      messageText = res.statusText || messageText;
    }
    throw new Error(messageText);
  }

  return res.json() as Promise<T>;
}

export type HeaderRecord = Record<string, string>;

export function buildHeaders(extra: HeaderRecord = {}): HeaderRecord {
  return {
    "Content-Type": "application/json",
    ...extra,
  };
}

/**
 * Build a URL-encoded query string from an object, skipping null/undefined/"".
 * Use:  `${API}/foo?${buildQuery({ page, status })}`
 */
export function buildQuery(
  params: Record<string, string | number | boolean | null | undefined> = {},
): string {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") q.append(k, String(v));
  });
  return q.toString();
}

/**
 * Standard JSON request headers.
 *
 * - The access JWT lives in an httpOnly cookie set by the backend, so we
 *   don't add an `Authorization` header here. Always pair callers with
 *   `credentials: "include"` (see `apiFetch`).
 * - The backend requires a double-submit CSRF token for mutating requests.
 *   We always echo the (non-httpOnly) `csrf_token` cookie back via the
 *   X-CSRF-Token header when present — the backend ignores it on safe
 *   methods, so the extra header is harmless on GETs.
 */
export function authHeaders(extra: HeaderRecord = {}): HeaderRecord {
  const headers = buildHeaders(extra);
  const csrf = readCookie(CSRF_COOKIE);
  if (csrf) headers[CSRF_HEADER] = csrf;
  return headers;
}

export interface ApiFetchOptions extends Omit<RequestInit, "headers"> {
  headers?: HeaderRecord;
}

/**
 * Thin wrapper around fetch() that:
 *   - Always includes credentials so the access cookie is sent
 *   - Always adds the CSRF header (no-op on GETs server-side)
 *   - Routes the response through `handleResponse` (auto-logout on 401)
 *
 *   const data = await apiFetch<MyShape>("/build-plans", { method: "GET" });
 */
export async function apiFetch<T = unknown>(
  url: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const headers = authHeaders(options.headers ?? {});
  const res = await fetch(url, {
    ...options,
    method,
    headers,
    credentials: options.credentials ?? "include",
  });
  return handleResponse<T>(res);
}

// Allow the auth flow to reset the latch after a successful re-login.
export function resetAuthGuard(): void {
  unauthorizedHandled = false;
}

/**
 * For non-JSON responses (e.g. streaming endpoints) where you can't run the
 * body through `handleResponse`. Detects 401 and triggers the same auto-logout
 * + redirect flow. Returns true if the response was unauthorized so the caller
 * can early-exit.
 */
export async function handleUnauthorized(res: Response): Promise<boolean> {
  if (res.status === 401 && !isAuthEndpoint(res.url)) {
    let detail = "Session expired. Please sign in again.";
    try {
      const body = (await res.clone().json()) as ErrorBody;
      detail = body.detail || body.message || body.error?.message || detail;
    } catch {
      /* ignore */
    }
    forceLogout(detail);
    return true;
  }
  return false;
}
