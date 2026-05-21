import { API } from "@/config";
import { authHeaders, handleResponse } from "@/shared/services/helper";

/**
 * Fetch users.
 *
 * Backend now returns a paginated wrapper `{ data, page, page_size, total }`.
 * Most legacy callers expect a plain array. We expose two shapes:
 *   - `fetchUsers(params)` -> array of users (for backward-compatible callers).
 *   - `fetchUsersPaged(params)` -> `{ data, page, page_size, total }` (for new
 *     paginated tables).
 */
export async function fetchUsersPaged(params = {}) {
  const q = new URLSearchParams(params).toString();
  const res = await fetch(`${API}/users/?${q}`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}

export async function fetchUsers(params = {}) {
  const result = await fetchUsersPaged(params);
  if (Array.isArray(result)) return result;
  return result?.data ?? [];
}

export async function createUser(data) {
  const res = await fetch(`${API}/users/`, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function updateUser(id, data) {
  const res = await fetch(`${API}/users/${id}`, {
    method: "PATCH",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function activateUser(id) {
  const res = await fetch(`${API}/users/${id}/activate`, {
    method: "PATCH",
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}

export async function deactivateUser(id) {
  const res = await fetch(`${API}/users/${id}/deactivate`, {
    method: "PATCH",
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}

export async function setUserRoles(id, roleIds) {
  const res = await fetch(`${API}/users/${id}/roles`, {
    method: "PATCH",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify({ role_ids: roleIds }),
  });
  return handleResponse(res);
}

export async function mergeUsers(primaryId, duplicateId) {
  const res = await fetch(`${API}/users/${primaryId}/merge/${duplicateId}`, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}
