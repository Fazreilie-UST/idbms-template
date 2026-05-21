// Runtime configuration. `window._env_` is injected by `public/env.js` (dev)
// or by `entrypoint.sh` (Docker / production). Both define `API_URL` as the
// backend's origin, e.g. "http://localhost:8000". The API version prefix is
// appended here so callers can use a single `API` constant for all requests.
const RAW_API_ORIGIN: string =
  (typeof window !== "undefined" && window._env_?.API_URL) ||
  "http://localhost:8000";

const API_ORIGIN: string = RAW_API_ORIGIN.replace(/\/+$/, "");
export const API: string = `${API_ORIGIN}/api/v1`;

/**
 * Resolve a path returned by the backend (e.g. `/static/profile-pictures/foo.jpg`)
 * to an absolute URL on the backend origin. Pass-through for already-absolute
 * URLs and nullish input.
 */
export function resolveBackendUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (/^https?:\/\//i.test(path)) return path;
  return `${API_ORIGIN}${path.startsWith("/") ? path : `/${path}`}`;
}
