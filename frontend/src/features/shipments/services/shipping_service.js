import { API } from "@/config";
import { authHeaders, buildQuery, handleResponse } from "@/shared/services/helper";

export async function fetchShippings(params = {}) {
  const res = await fetch(`${API}/shippings?${buildQuery(params)}`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}

export async function fetchShippingById(id) {
  const res = await fetch(`${API}/shippings/${id}`, { headers: authHeaders(), credentials: "include" });
  return handleResponse(res);
}
