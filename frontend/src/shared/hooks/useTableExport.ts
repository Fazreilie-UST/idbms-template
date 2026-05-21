import { useCallback, useState } from "react";
import { message } from "antd";
import { fetchAllPaginatedRows } from "@/shared/utils/fetchAllPaginatedRows";
import type { FileType } from "@/shared/utils/createStandardTableExporters";
import type { ExportRow } from "@/shared/utils/exportHelpers";

const DEFAULT_EXPORT_BATCH_SIZE = 500;
const ALLOWED_FILE_TYPES = new Set<FileType>(["json", "csv", "pdf", "xlsx"]);

interface ErrorWithResponse {
  message?: unknown;
  detail?: unknown;
  response?: { data?: { message?: unknown; detail?: unknown } };
}

function getErrorMessage(error: unknown, fallback = "Something went wrong"): string {
  if (typeof error === "string") return error;

  const e = error as ErrorWithResponse | null | undefined;
  if (!e) return fallback;

  if (typeof e.message === "string") return e.message;
  if (typeof e.detail === "string") return e.detail;

  if (Array.isArray(e.detail)) {
    return e.detail
      .map((item: unknown) =>
        item && typeof item === "object" && "msg" in (item as Record<string, unknown>)
          ? String((item as Record<string, unknown>).msg)
          : JSON.stringify(item),
      )
      .join(", ");
  }

  const respData = e.response?.data;
  if (respData) {
    if (typeof respData.message === "string") return respData.message;
    if (typeof respData.detail === "string") return respData.detail;
    if (Array.isArray(respData.detail)) {
      return respData.detail
        .map((item: unknown) =>
          item && typeof item === "object" && "msg" in (item as Record<string, unknown>)
            ? String((item as Record<string, unknown>).msg)
            : JSON.stringify(item),
        )
        .join(", ");
    }
  }

  return fallback;
}

type FetchPageFn = (page: number, pageSize: number) => Promise<{ items?: ExportRow[]; total?: number | string }>;

interface UseTableExportOptions {
  batchSize?: number;
  buildFilename?: (fileType: FileType, rows: ExportRow[]) => void;
}

export interface UseTableExportResult {
  exporting: boolean;
  getExportRows: () => Promise<ExportRow[]>;
  runExport: (
    fileType: FileType,
    exportFn: (rows: ExportRow[]) => void | Promise<void>,
    successMessage: string,
    errorMessage: string,
  ) => Promise<void>;
}

export default function useTableExport(
  fetchPageFn: FetchPageFn,
  { batchSize = DEFAULT_EXPORT_BATCH_SIZE, buildFilename }: UseTableExportOptions = {},
): UseTableExportResult {
  const [exporting, setExporting] = useState(false);

  const getExportRows = useCallback(async () => {
    return fetchAllPaginatedRows<ExportRow>(fetchPageFn, batchSize);
  }, [fetchPageFn, batchSize]);

  const runExport: UseTableExportResult["runExport"] = useCallback(
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
    [getExportRows, buildFilename],
  );

  return {
    exporting,
    getExportRows,
    runExport,
  };
}
