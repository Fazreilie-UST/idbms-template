import { API } from "@/config";
import { apiFetch, authHeaders, buildHeaders, handleResponse } from "@/shared/services/helper";

export async function login(email, password) {
  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: buildHeaders(),
    credentials: "include",
    body: JSON.stringify({ email, password }),
  });

  return handleResponse(res);
}

/** Fetch the currently authenticated user (full profile, including avatar URL). */
export function getMyProfile() {
  return apiFetch(`${API}/auth/me`, { method: "GET" });
}

/**
 * Upload (or replace) the current user's profile picture.
 * Returns the updated user record.
 */
export async function uploadAvatar(file) {
  const formData = new FormData();
  formData.append("file", file);

  // Don't use buildHeaders(): fetch must set the multipart boundary itself.
  // We still need the CSRF header on this mutating call.
  const headers = authHeaders();
  delete headers["Content-Type"];

  const res = await fetch(`${API}/users/me/avatar`, {
    method: "POST",
    headers,
    credentials: "include",
    body: formData,
  });

  return handleResponse(res);
}

/** Remove the current user's profile picture. Returns the updated user. */
export function deleteAvatar() {
  return apiFetch(`${API}/users/me/avatar`, { method: "DELETE" });
}
