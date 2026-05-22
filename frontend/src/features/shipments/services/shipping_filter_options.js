import { API } from "@/config";
import { authHeaders, handleResponse } from "@/shared/services/helper";

export async function fetchShippingFilterOptions() {
  const res = await fetch(`${API}/shippings/filter-options`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}
