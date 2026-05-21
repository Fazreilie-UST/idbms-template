import { API } from "@/config";
import { authHeaders, handleResponse } from "@/shared/services/helper";

export async function fetchRoles() {
  const res = await fetch(`${API}/roles/`, { headers: authHeaders(), credentials: "include" });
  return handleResponse(res);
}

export async function createRole(data) {
  const res = await fetch(`${API}/roles/`, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function updateRole(id, data) {
  const res = await fetch(`${API}/roles/${id}`, {
    method: "PATCH",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function deleteRole(id) {
  const res = await fetch(`${API}/roles/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}

export async function setRolePermissions(id, permissionIds) {
  const res = await fetch(`${API}/roles/${id}/permissions`, {
    method: "PATCH",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify({ permission_ids: permissionIds }),
  });
  return handleResponse(res);
}

export async function fetchPermissions() {
  const res = await fetch(`${API}/permissions/`, { headers: authHeaders(), credentials: "include" });
  return handleResponse(res);
}
