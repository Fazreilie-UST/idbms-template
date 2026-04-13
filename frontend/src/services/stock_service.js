import axios from "axios";
import { API } from "../config";
import { buildHeaders, handleResponse } from "./helper";

async function fetchPaginated(
  url,
  page = 1,
  pageSize = 10,
  token = null,
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
    headers: buildHeaders(token),
  });

  return handleResponse(res);
}

export async function fetchStockMaster(
  page = 1,
  pageSize = 10,
  token = null,
  sortBy = null,
  sortOrder = null
) {
  return fetchPaginated(
    "/stocks/master",
    page,
    pageSize,
    token,
    sortBy,
    sortOrder
  );
}

export async function fetchDates(
  page = 1,
  pageSize = 10,
  token = null,
  sortBy = null,
  sortOrder = null
) {
  return fetchPaginated("/stocks/dates", page, pageSize, token, sortBy, sortOrder);
}

export async function fetchStatements(
  page = 1,
  pageSize = 10,
  token = null,
  sortBy = null,
  sortOrder = null
) {
  return fetchPaginated(
    "/stocks/statements",
    page,
    pageSize,
    token,
    sortBy,
    sortOrder
  );
}

export async function fetchMetrics(
  page = 1,
  pageSize = 10,
  token = null,
  sortBy = null,
  sortOrder = null
) {
  return fetchPaginated("/stocks/metrics", page, pageSize, token, sortBy, sortOrder);
}

export async function fetchFinancialFacts(
  page = 1,
  pageSize = 10,
  token = null,
  sortBy = null,
  sortOrder = null
) {
  return fetchPaginated(
    "/stocks/facts",
    page,
    pageSize,
    token,
    sortBy,
    sortOrder
  );
}

export async function importFinancialFactsCsv(
  file,
  token = null,
  dryRun = false,
  replaceAll = false,
  onUploadProgress = null,
) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("dry_run", dryRun ? "true" : "false");
  formData.append("replace_all", replaceAll ? "true" : "false");

  const res = await axios.post(`${API}/stocks/facts/import-csv`, formData, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
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

export async function previewStockStatementExplorer(payload, token = null) {
  const res = await fetch(`${API}/stocks/explorer/preview`, {
    method: "POST",
    headers: buildHeaders(token),
    body: JSON.stringify(payload),
  });

  return handleResponse(res);
}

export async function importDimStockCsv(
  file,
  token = null,
  dryRun = false,
  replaceAll = false,
  onUploadProgress = null
) {
  return importDimensionCsv(
    "/stocks/master/import-csv",
    file,
    token,
    dryRun,
    replaceAll,
    onUploadProgress
  );
}

export async function importDimDateCsv(
  file,
  token = null,
  dryRun = false,
  replaceAll = false,
  onUploadProgress = null
) {
  return importDimensionCsv(
    "/stocks/dates/import-csv",
    file,
    token,
    dryRun,
    replaceAll,
    onUploadProgress
  );
}

export async function importDimStatementCsv(
  file,
  token = null,
  dryRun = false,
  replaceAll = false,
  onUploadProgress = null
) {
  return importDimensionCsv(
    "/stocks/statements/import-csv",
    file,
    token,
    dryRun,
    replaceAll,
    onUploadProgress
  );
}

export async function importDimMetricCsv(
  file,
  token = null,
  dryRun = false,
  replaceAll = false,
  onUploadProgress = null
) {
  return importDimensionCsv(
    "/stocks/metrics/import-csv",
    file,
    token,
    dryRun,
    replaceAll,
    onUploadProgress
  );
}

async function importDimensionCsv(
  url,
  file,
  token = null,
  dryRun = false,
  replaceAll = false,
  onUploadProgress = null,
) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("dry_run", dryRun ? "true" : "false");
  formData.append("replace_all", replaceAll ? "true" : "false");

  const res = await axios.post(`${API}${url}`, formData, {
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
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