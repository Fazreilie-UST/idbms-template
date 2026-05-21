import axios from "axios";
import { API } from "@/config";
import { authHeaders, handleResponse } from "@/shared/services/helper";

// `token` parameters are kept for backwards compatibility with `useServerTable`
// and existing call sites; they are ignored because authentication now relies
// on the httpOnly access-token cookie. The mutating axios calls add an
// X-CSRF-Token header via authHeaders().

function csrfHeaderForUpload() {
  // FormData uploads need the CSRF header but NOT a Content-Type override
  // (axios sets the multipart boundary itself). authHeaders adds the CSRF
  // token; we strip the JSON Content-Type so axios picks the right one.
  const headers = authHeaders();
  delete headers["Content-Type"];
  return headers;
}

async function fetchPaginated(
  url,
  page = 1,
  pageSize = 10,
  sortBy = null,
  sortOrder = null
) {
  const safePage = Math.max(1, Number(page) || 1);
  const safePageSize = Math.min(500, Math.max(1, Number(pageSize) || 10));
  const skip = (safePage - 1) * safePageSize;

  const params = new URLSearchParams({
    skip: String(skip),
    limit: String(safePageSize),
  });

  if (sortBy) {
    params.append("sort_by", sortBy);
  }

  if (sortOrder) {
    params.append("sort_order", sortOrder);
  }

  const res = await fetch(`${API}${url}?${params.toString()}`, {
    headers: authHeaders(),
    credentials: "include",
  });

  return handleResponse(res);
}

export async function fetchStockMaster(page = 1, pageSize = 10, _token = null, sortBy = null, sortOrder = null) {
  void _token;
  return fetchPaginated("/stocks/master", page, pageSize, sortBy, sortOrder);
}

export async function fetchDates(page = 1, pageSize = 10, _token = null, sortBy = null, sortOrder = null) {
  void _token;
  return fetchPaginated("/stocks/dates", page, pageSize, sortBy, sortOrder);
}

export async function fetchStatements(page = 1, pageSize = 10, _token = null, sortBy = null, sortOrder = null) {
  void _token;
  return fetchPaginated("/stocks/statements", page, pageSize, sortBy, sortOrder);
}

export async function fetchMetrics(page = 1, pageSize = 10, _token = null, sortBy = null, sortOrder = null) {
  void _token;
  return fetchPaginated("/stocks/metrics", page, pageSize, sortBy, sortOrder);
}

export async function fetchFinancialFacts(page = 1, pageSize = 10, _token = null, sortBy = null, sortOrder = null) {
  void _token;
  return fetchPaginated("/stocks/facts", page, pageSize, sortBy, sortOrder);
}

export async function importFinancialFactsCsv(
  file,
  _token = null,
  dryRun = false,
  replaceAll = false,
  onUploadProgress = null,
) {
  void _token;
  const formData = new FormData();
  formData.append("file", file);
  formData.append("dry_run", dryRun ? "true" : "false");
  formData.append("replace_all", replaceAll ? "true" : "false");

  const res = await axios.post(`${API}/stocks/facts/import-csv`, formData, {
    headers: csrfHeaderForUpload(),
    withCredentials: true,
    onUploadProgress: (progressEvent) => {
      if (!onUploadProgress) return;
      const total = progressEvent.total || 0;
      const loaded = progressEvent.loaded || 0;
      const percent = total > 0 ? Math.round((loaded * 100) / total) : 0;
      onUploadProgress(percent);
    },
  });

  return res.data;
}

export async function previewStockStatementExplorer(payload, _token = null) {
  void _token;
  const res = await fetch(`${API}/stocks/explorer/preview`, {
    method: "POST",
    headers: authHeaders(),
    credentials: "include",
    body: JSON.stringify(payload),
  });

  return handleResponse(res);
}

export async function importDimStockCsv(file, token = null, dryRun = false, replaceAll = false, onUploadProgress = null) {
  return importDimensionCsv("/stocks/master/import-csv", file, token, dryRun, replaceAll, onUploadProgress);
}

export async function importDimDateCsv(file, token = null, dryRun = false, replaceAll = false, onUploadProgress = null) {
  return importDimensionCsv("/stocks/dates/import-csv", file, token, dryRun, replaceAll, onUploadProgress);
}

export async function importDimStatementCsv(file, token = null, dryRun = false, replaceAll = false, onUploadProgress = null) {
  return importDimensionCsv("/stocks/statements/import-csv", file, token, dryRun, replaceAll, onUploadProgress);
}

export async function importDimMetricCsv(file, token = null, dryRun = false, replaceAll = false, onUploadProgress = null) {
  return importDimensionCsv("/stocks/metrics/import-csv", file, token, dryRun, replaceAll, onUploadProgress);
}

async function importDimensionCsv(
  url,
  file,
  _token = null,
  dryRun = false,
  replaceAll = false,
  onUploadProgress = null,
) {
  void _token;
  const formData = new FormData();
  formData.append("file", file);
  formData.append("dry_run", dryRun ? "true" : "false");
  formData.append("replace_all", replaceAll ? "true" : "false");

  const res = await axios.post(`${API}${url}`, formData, {
    headers: csrfHeaderForUpload(),
    withCredentials: true,
    onUploadProgress: (progressEvent) => {
      if (!onUploadProgress) return;
      const total = progressEvent.total || 0;
      const loaded = progressEvent.loaded || 0;
      const percent = total > 0 ? Math.round((loaded * 100) / total) : 0;
      onUploadProgress(percent);
    },
  });

  return res.data;
}
