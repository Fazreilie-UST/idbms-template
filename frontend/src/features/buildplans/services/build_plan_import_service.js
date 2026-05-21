import { API } from "@/config";
import { authHeaders, handleResponse, handleUnauthorized } from "@/shared/services/helper";

const BASE = `${API}/build-plan-imports`;

// FormData uploads need the CSRF header but NOT a JSON Content-Type override
// (fetch sets the multipart boundary itself). authHeaders adds the CSRF
// token; we strip the JSON Content-Type so the browser picks the right one.
function uploadHeaders() {
  const h = authHeaders();
  delete h["Content-Type"];
  return h;
}

// Use the shared response helper so 401s trigger the global auto-logout flow.
// Wrap it so 204 (No Content) responses still return null instead of trying
// to parse an empty body as JSON.
async function handle(res) {
  if (res.status === 204) {
    // Still let handleResponse run its 401 check on the (empty) body before
    // returning, in case the server downgraded the response.
    if (res.status === 401) return handleResponse(res);
    return null;
  }
  return handleResponse(res);
}

export async function uploadBuildPlanFile(file, { autoProcess = false } = {}) {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${BASE}?auto_process=${autoProcess}`, {
    method: "POST",
    headers: uploadHeaders(),
    credentials: "include",
    body: form,
  });
  return handle(res); // -> { record, duplicate }
}

export async function listBuildPlanImports({
  page = 1,
  pageSize = 20,
  status,
  sort_by,
  sort_order,
  mine,
} = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (status) params.append("status", status);
  if (sort_by) params.append("sort_by", sort_by);
  if (sort_order) params.append("sort_order", sort_order);
  if (mine) params.append("mine", "true");

  const res = await fetch(`${BASE}?${params.toString()}`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return handle(res);
}

/**
 * List the rows parsed from the file's "Shipping Info" sheet.
 * Returns: BuildPlanImportShippingInfoResponse[]
 */
export async function getImportShippingInfos(id) {
  const res = await fetch(`${BASE}/${id}/shipping-infos`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return handle(res);
}

/**
 * List the rows parsed from the file's "Si" sheet.
 * Returns: BuildPlanImportSiRowResponse[]
 */
export async function getImportSiRows(id) {
  const res = await fetch(`${BASE}/${id}/si-rows`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return handle(res);
}

/**
 * Manually update WW / Year / Rev on an uploaded file. Useful when the
 * filename does not match the auto-parser. If the row was `skipped` purely
 * for missing metadata, the server flips it back to `pending`.
 */
export async function updateBuildPlanImportMetadata(id, { work_week, work_year, file_revision }) {
  const res = await fetch(`${BASE}/${id}`, {
    method: "PATCH",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify({ work_week, work_year, file_revision }),
  });
  return handle(res);
}

export async function deleteBuildPlanImport(id, { deleteFile = true } = {}) {
  const res = await fetch(`${BASE}/${id}?delete_file=${deleteFile}`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
  });
  return handle(res);
}

/**
 * Pre-fetch the number of build-plan rows each uploaded file will produce.
 * Used to size the per-build-plan progress bar before processing starts.
 * Returns: { counts: { [id]: number }, not_found: number[], skipped: number[] }
 */
export async function getBuildPlanCounts(ids) {
  const res = await fetch(`${BASE}/plan-counts`, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify({ ids }),
  });
  return handle(res);
}

/**
 * Process one import file with streaming per-build-plan progress events.
 *
 *   await streamProcessBuildPlanImport(id, (evt) => {
 *     // evt = { event, file_id, processed, total, ...extras }
 *   });
 *
 * Resolves once the stream is closed. The final event is either
 * { event: "complete", record } or { event: "error", message }.
 */
export async function streamProcessBuildPlanImport(id, onEvent) {
  const res = await fetch(`${BASE}/${id}/process-stream`, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
  });
  if (await handleUnauthorized(res)) {
    // The redirect / store reset is already in flight; bail out so the caller
    // doesn't try to interpret the 401 body as a stream.
    throw new Error("Session expired. Please sign in again.");
  }
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Stream failed: ${res.status}`);
  }
  if (!res.body) {
    throw new Error("Streaming responses are not supported by this browser");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let lastEvent = null;

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let newlineIdx;
    while ((newlineIdx = buffer.indexOf("\n")) !== -1) {
      const line = buffer.slice(0, newlineIdx).trim();
      buffer = buffer.slice(newlineIdx + 1);
      if (!line) continue;
      try {
        const evt = JSON.parse(line);
        lastEvent = evt;
        onEvent?.(evt);
      } catch {
        // Ignore malformed line; the server should never emit one.
      }
    }
  }

  // Flush any trailing partial line.
  const tail = buffer.trim();
  if (tail) {
    try {
      const evt = JSON.parse(tail);
      lastEvent = evt;
      onEvent?.(evt);
    } catch {
      /* ignore */
    }
  }

  return lastEvent;
}
