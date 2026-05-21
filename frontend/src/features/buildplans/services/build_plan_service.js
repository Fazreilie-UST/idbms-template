import { API } from "@/config";
import { authHeaders, buildQuery } from "@/shared/services/helper";

async function unwrap(res) {
  if (!res.ok) {
    throw new Error(await res.text());
  }
  return res.json();
}

export async function fetchBuildPlans(params = {}) {
  const res = await fetch(`${API}/build-plans?${buildQuery(params)}`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return unwrap(res);
}

export async function fetchBuildPlanById(id) {
  const res = await fetch(`${API}/build-plans/${id}`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return unwrap(res);
}

/**
 * Aggregated Shipping Info + Si rows captured from every import file that
 * touched a build plan sharing this plan's family + Form Factor.
 * Returns: { build_plan_id, family_form_factor_id, family_code, form_factor,
 *            files: [...], shipping_infos: [...], si_rows: [...] }
 */
export async function fetchBuildPlanExtraSheets(id) {
  const res = await fetch(`${API}/build-plans/${id}/extra-sheets`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return unwrap(res);
}

export async function fetchBuildPlanFilterOptions() {
  const res = await fetch(`${API}/build-plans/filter-options`, {
    method: "GET",
    headers: authHeaders(),
    credentials: "include",
  });

  if (!res.ok) {
    const text = await res.text();
    console.error("Filter options failed:", text);
    throw new Error(text);
  }

  return res.json();
}

export async function grantBuildPlanAccess({ build_plan_ids, user_ids, access_type, scope }) {
  const res = await fetch(`${API}/build-plans/access`, {
    method: "POST",
    headers: { ...authHeaders(), "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ build_plan_ids, user_ids, access_type, ...(scope ? { scope } : {}) }),
  });
  return unwrap(res);
}

export async function fetchBuildPlanAccess(buildPlanId) {
  const res = await fetch(`${API}/build-plans/${buildPlanId}/access`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return unwrap(res);
}
