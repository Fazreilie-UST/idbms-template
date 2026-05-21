import { API } from "@/config";
import { authHeaders, handleResponse } from "@/shared/services/helper";

export async function fetchBuildRequestFilterOptions() {
  const res = await fetch(`${API}/build-requests/filter-options`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}
