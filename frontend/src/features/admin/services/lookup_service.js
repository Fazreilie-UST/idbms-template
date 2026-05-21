import { API } from "@/config";
import { authHeaders, handleResponse } from "@/shared/services/helper";

// ---------- Forwarders ----------
export async function fetchForwarders() {
  const res = await fetch(`${API}/forwarders/`, { headers: authHeaders(), credentials: "include" });
  return handleResponse(res);
}
export async function createForwarder(data) {
  const res = await fetch(`${API}/forwarders/`, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}
export async function updateForwarder(id, data) {
  const res = await fetch(`${API}/forwarders/${id}`, {
    method: "PATCH",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}
export async function deleteForwarder(id) {
  const res = await fetch(`${API}/forwarders/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}

// ---------- Build Notes ----------
export async function fetchBuildNotes() {
  const res = await fetch(`${API}/build-notes/`, { headers: authHeaders(), credentials: "include" });
  return handleResponse(res);
}
export async function createBuildNote(data) {
  const res = await fetch(`${API}/build-notes/`, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}
export async function updateBuildNote(id, data) {
  const res = await fetch(`${API}/build-notes/${id}`, {
    method: "PATCH",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}
export async function deleteBuildNote(id) {
  const res = await fetch(`${API}/build-notes/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}

export async function mergeBuildNotes(primaryId, duplicateId) {
  const res = await fetch(`${API}/build-notes/${primaryId}/merge/${duplicateId}`, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}

// ---------- Support Activities ----------
export async function fetchSupportActivities() {
  const res = await fetch(`${API}/support-activities/`, { headers: authHeaders(), credentials: "include" });
  return handleResponse(res);
}
export async function createSupportActivity(data) {
  const res = await fetch(`${API}/support-activities/`, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}
export async function updateSupportActivity(id, data) {
  const res = await fetch(`${API}/support-activities/${id}`, {
    method: "PATCH",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}
export async function deleteSupportActivity(id) {
  const res = await fetch(`${API}/support-activities/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}

// ---------- Generic name-only CRUD factory ----------
function makeNameCrud(path) {
  return {
    list: async () => {
      const res = await fetch(`${API}/${path}/`, {
        headers: authHeaders(),
        credentials: "include",
      });
      return handleResponse(res);
    },
    create: async (data) => {
      const res = await fetch(`${API}/${path}/`, {
        method: "POST",
        headers: authHeaders(),
        credentials: "include",
        body: JSON.stringify(data),
      });
      return handleResponse(res);
    },
    update: async (id, data) => {
      const res = await fetch(`${API}/${path}/${id}`, {
        method: "PATCH",
        headers: authHeaders(),
        credentials: "include",
        body: JSON.stringify(data),
      });
      return handleResponse(res);
    },
    remove: async (id) => {
      const res = await fetch(`${API}/${path}/${id}`, {
        method: "DELETE",
        headers: authHeaders(),
        credentials: "include",
      });
      return handleResponse(res);
    },
  };
}

// Form Factors
const ff = makeNameCrud("form-factors");
export const fetchFormFactors = ff.list;
export const createFormFactor = ff.create;
export const updateFormFactor = ff.update;
export const deleteFormFactor = ff.remove;

// Silicon Steppings
const ss = makeNameCrud("silicon-steppings");
export const fetchSiliconSteppings = ss.list;
export const createSiliconStepping = ss.create;
export const updateSiliconStepping = ss.update;
export const deleteSiliconStepping = ss.remove;

// Components
const comp = makeNameCrud("components");
export const createComponent = comp.create;
export const updateComponent = comp.update;
export const deleteComponent = comp.remove;

// Suppliers
const sup = makeNameCrud("suppliers");
export const fetchSuppliers = sup.list;
export const createSupplier = sup.create;
export const updateSupplier = sup.update;
export const deleteSupplier = sup.remove;

// Build Descriptions (custom schema: support_activity_id + description)
export async function fetchBuildDescriptions() {
  const res = await fetch(`${API}/build-descriptions/`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}
export async function createBuildDescription(data) {
  const res = await fetch(`${API}/build-descriptions/`, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}
export async function updateBuildDescription(id, data) {
  const res = await fetch(`${API}/build-descriptions/${id}`, {
    method: "PATCH",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}
export async function deleteBuildDescription(id) {
  const res = await fetch(`${API}/build-descriptions/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}

// Addresses
export async function fetchAddresses() {
  const res = await fetch(`${API}/addresses/`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}
export async function createAddress(data) {
  const res = await fetch(`${API}/addresses/`, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}
export async function updateAddress(id, data) {
  const res = await fetch(`${API}/addresses/${id}`, {
    method: "PATCH",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}
export async function deleteAddress(id) {
  const res = await fetch(`${API}/addresses/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}

// Warehouses
export async function fetchWarehouses() {
  const res = await fetch(`${API}/warehouses/`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}
export async function createWarehouse(data) {
  const res = await fetch(`${API}/warehouses/`, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}
export async function updateWarehouse(id, data) {
  const res = await fetch(`${API}/warehouses/${id}`, {
    method: "PATCH",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(data),
  });
  return handleResponse(res);
}
export async function deleteWarehouse(id) {
  const res = await fetch(`${API}/warehouses/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}

// ---------- Component <-> Supplier <-> Family tree ----------
export async function fetchComponentSupplierTree() {
  const res = await fetch(`${API}/component-suppliers/tree`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return handleResponse(res);
}

export async function addComponentSupplier(componentId, supplierId, familyIds = []) {
  const res = await fetch(`${API}/component-suppliers/${componentId}/suppliers`, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify({ supplier_id: supplierId, family_ids: familyIds }),
  });
  return handleResponse(res);
}

export async function removeComponentSupplier(componentId, supplierId) {
  const res = await fetch(
    `${API}/component-suppliers/${componentId}/suppliers/${supplierId}`,
    {
      method: "DELETE",
      headers: authHeaders(),
      credentials: "include",
    }
  );
  return handleResponse(res);
}

export async function setComponentSupplierFamilies(
  componentId,
  supplierId,
  familyIds
) {
  const res = await fetch(
    `${API}/component-suppliers/${componentId}/suppliers/${supplierId}/families`,
    {
      method: "PUT",
      headers: authHeaders(),
      credentials: "include",
      body: JSON.stringify({ family_ids: familyIds }),
    }
  );
  return handleResponse(res);
}
