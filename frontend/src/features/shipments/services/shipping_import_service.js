import { API } from "@/config";
import { authHeaders, handleResponse, handleUnauthorized } from "@/shared/services/helper";

const BASE = `${API}/shipping-imports`;

function uploadHeaders() {
  const h = authHeaders();
  delete h["Content-Type"];
  return h;
}

async function handle(res) {
  if (res.status === 204) {
    if (res.status === 401) return handleResponse(res);
    return null;
  }
  return handleResponse(res);
}

export async function uploadShippingImportFile(file, { autoProcess = false } = {}) {
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

export async function listShippingImports({ page = 1, pageSize = 20, status } = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  if (status) params.append("status", status);

  const res = await fetch(`${BASE}?${params.toString()}`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return handle(res);
}

export async function deleteShippingImport(id, { deleteFile = true } = {}) {
  const res = await fetch(`${BASE}/${id}?delete_file=${deleteFile}`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
  });
  return handle(res);
}

/**
 * Process one import file with streaming per-row progress events.
 * Resolves once the stream is closed. The final event is either
 * { event: "complete", record } or { event: "error", message }.
 */
export async function streamProcessShippingImport(id, onEvent) {
  const res = await fetch(`${BASE}/${id}/process-stream`, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
  });
  if (await handleUnauthorized(res)) {
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
        /* ignore */
      }
    }
  }

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
