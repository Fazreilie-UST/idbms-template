import { API } from "@/config";
import { authHeaders } from "@/shared/services/helper";

/**
 * Build a query string supporting array values (repeated keys), which is
 * the format FastAPI expects for List[str] query params.
 */
function buildDashboardQuery(params = {}) {
  const q = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v === undefined || v === null || v === "") return;
    if (Array.isArray(v)) {
      v.forEach((item) => {
        if (item !== undefined && item !== null && item !== "") {
          q.append(k, String(item));
        }
      });
    } else {
      q.append(k, String(v));
    }
  });
  return q.toString();
}

/**
 * Translate the frontend filter store shape to the backend query-param names.
 * Backend accepts repeated keys for multi-value filters.
 */
function filtersToParams(filters = {}) {
  return {
    year: filters.year ?? undefined,
    family_code: filters.familyCodes ?? [],
    form_factor: filters.formFactors ?? [],
    support_activity: filters.supportActivities ?? [],
    status: filters.statuses ?? [],
    silicon_stepping: filters.siliconSteppings ?? [],
  };
}

async function unwrap(res) {
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function get(path, params = {}) {
  const qs = buildDashboardQuery(params);
  const url = `${API}/dashboard/business${path}${qs ? `?${qs}` : ""}`;
  const res = await fetch(url, {
    headers: authHeaders(),
    credentials: "include",
  });
  return unwrap(res);
}

export function fetchKpis(filters) {
  return get("/kpis", filtersToParams(filters));
}

export function fetchFamilyBreakdown(filters, metric = "boards") {
  return get("/family-breakdown", { ...filtersToParams(filters), metric });
}

export function fetchFamilyAttributeBreakdown(filters) {
  return get("/family-attribute-breakdown", filtersToParams(filters));
}

export function fetchSupportActivityBreakdown(filters, metric = "builds") {
  return get("/support-activity-breakdown", {
    ...filtersToParams(filters),
    metric,
  });
}

export function fetchSiliconStepping(filters) {
  return get("/silicon-stepping", filtersToParams(filters));
}

export function fetchLookups() {
  return get("/lookups", {});
}

// ---------------------------------------------------------------------------
// Phase 2
// ---------------------------------------------------------------------------

export function fetchRequiredQuantityTop(filters, limit = 15) {
  return get("/required-quantity-top", { ...filtersToParams(filters), limit });
}

export function fetchMilestoneTimeline(filters, metric = "builds") {
  return get("/milestone-timeline", { ...filtersToParams(filters), metric });
}

export function fetchFamilyComparison(familyCode, filters) {
  return get(`/family-comparison/${encodeURIComponent(familyCode)}`, filtersToParams(filters));
}

export function fetchSupplierComponent(componentName, metric = "builds", slotCode = null, filters = {}) {
  const params = {
    ...filtersToParams(filters),
    component_name: componentName,
    metric,
    ...(slotCode ? { slot_code: slotCode } : {}),
  };
  return get("/supplier-component", params);
}

export function fetchSupplierComponentDetail(componentName, slotCode = null, filters = {}) {
  const params = {
    ...filtersToParams(filters),
    component_name: componentName,
    ...(slotCode ? { slot_code: slotCode } : {}),
  };
  return get("/supplier-component-detail", params);
}

export function fetchSupplierComponentByPcbSupplier(
  componentName,
  slotCode = null,
  filters = {},
) {
  const params = {
    ...filtersToParams(filters),
    component_name: componentName,
    ...(slotCode ? { slot_code: slotCode } : {}),
  };
  return get("/supplier-component-by-pcb-supplier", params);
}


