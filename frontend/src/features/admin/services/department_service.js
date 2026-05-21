import { API } from "@/config";
import { authHeaders, handleResponse } from "@/shared/services/helper";

export async function fetchDepartments() {
  const res = await fetch(`${API}/departments/`, { headers: authHeaders(), credentials: "include" });
  return handleResponse(res);
}

export async function createDepartment(data) {
  const res = await fetch(`${API}/departments/`, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function updateDepartment(id, data) {
  const res = await fetch(`${API}/departments/${id}`, {
    method: "PATCH",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}

export async function deleteDepartment(id) {
  const res = await fetch(`${API}/departments/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}
