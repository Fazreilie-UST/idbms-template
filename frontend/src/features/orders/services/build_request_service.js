import { API } from "@/config";
import { authHeaders, buildQuery, handleResponse } from "@/shared/services/helper";

export async function fetchBuildRequests(params = {}) {
  const res = await fetch(`${API}/build-requests?${buildQuery(params)}`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}

export async function fetchBuildRequestById(id) {
  const res = await fetch(`${API}/build-requests/${id}`, { headers: authHeaders(), credentials: "include" });
  return handleResponse(res);
}

export async function fetchBuildRequestRevisions(id) {
  const res = await fetch(`${API}/build-requests/${id}/revisions`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}
