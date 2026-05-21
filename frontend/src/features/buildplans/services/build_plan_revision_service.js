import { API } from "@/config";
import { authHeaders, handleResponse } from "@/shared/services/helper";

export async function fetchBuildPlanRevisions(id) {
  const res = await fetch(`${API}/build-plans/${id}/revisions`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}

export async function createBuildPlanRevision(id, payload) {
  const res = await fetch(`${API}/build-plans/${id}/revisions`, {
    method: "POST",
    headers: {
      ...authHeaders(),
      "Content-Type": "application/json",
    },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return handleResponse(res);
}
