import { useCallback, useState } from "react";
import { message } from "antd";
import { fetchAllPaginatedRows } from "../utils/fetchAllPaginatedRows";

const DEFAULT_EXPORT_BATCH_SIZE = 500;
const ALLOWED_FILE_TYPES = new Set(["json", "csv", "pdf", "xlsx"]);

function getErrorMessage(error, fallback = "Something went wrong") {
  if (typeof error === "string") return error;
  if (typeof error?.message === "string") return error.message;
  if (typeof error?.detail === "string") return error.detail;

  if (Array.isArray(error?.detail)) {
    return error.detail.map((item) => item?.msg || JSON.stringify(item)).join(", ");
  }

  if (typeof error?.response?.data?.message === "string") {
    return error.response.data.message;
  }

  if (typeof error?.response?.data?.detail === "string") {
    return error.response.data.detail;
  }

  if (Array.isArray(error?.response?.data?.detail)) {
    return error.response.data.detail
      .map((item) => item?.msg || JSON.stringify(item))
      .join(", ");
  }

  return fallback;
}

export default function useTableExport(
  fetchPageFn,
  {
    batchSize = DEFAULT_EXPORT_BATCH_SIZE,
    buildFilename,
  } = {}
) {
  const [exporting, setExporting] = useState(false);

  const getExportRows = useCallback(async () => {
    return fetchAllPaginatedRows(fetchPageFn, batchSize);
  }, [fetchPageFn, batchSize]);

  const runExport = useCallback(
    async (fileType, exportFn, successMessage, errorMessage) => {
      try {
        if (!fileType || !ALLOWED_FILE_TYPES.has(fileType)) {
          message.warning("Invalid export type.");
          return;
        }

        setExporting(true);

        const rows = await getExportRows();
        buildFilename?.(fileType, rows);

        await exportFn?.(rows);

        message.success(successMessage || "Export completed.");
      } catch (error) {
        console.error("Export failed:", error);
        message.error(getErrorMessage(error, errorMessage || "Export failed"));
      } finally {
        setExporting(false);
      }
    },
    [getExportRows, buildFilename]
  );

  return {
    exporting,
    getExportRows,
    runExport,
  };
}