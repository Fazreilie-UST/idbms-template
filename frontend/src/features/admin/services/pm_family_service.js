import { API } from "@/config";
import { authHeaders, handleResponse } from "@/shared/services/helper";

const BASE = `${API}/pm-families`;

async function handle(res) {
  if (res.status === 204) return null;
  return handleResponse(res);
}

export async function fetchPMFamilies({ userId, familyId } = {}) {
  const params = new URLSearchParams();
  if (userId != null) params.append("user_id", String(userId));
  if (familyId != null) params.append("family_id", String(familyId));
  const qs = params.toString();
  const res = await fetch(`${BASE}${qs ? `?${qs}` : ""}`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return handle(res);
}

export async function createPMFamily({ user_id, family_id }) {
  const res = await fetch(BASE, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify({ user_id, family_id }),
  });
  return handle(res);
}

export async function deletePMFamily(id) {
  const res = await fetch(`${BASE}/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
  });
  return handle(res);
}

export async function fetchFamiliesLookup() {
  const res = await fetch(`${BASE}/families`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return handle(res);
}

export async function createFamily({ code, name, description }) {
  const res = await fetch(`${BASE}/families`, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify({ code, name, description }),
  });
  return handle(res);
}

export async function deleteFamily(id) {
  const res = await fetch(`${BASE}/families/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
  });
  return handle(res);
}
