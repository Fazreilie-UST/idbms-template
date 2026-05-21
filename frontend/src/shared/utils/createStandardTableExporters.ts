import { exportTableJson, exportTableCsv } from "@/shared/utils/tableDataExport";
import { exportTablePdf } from "@/shared/utils/tablePdfExport";
import type { ExportColumn, ExportRow } from "@/shared/utils/exportHelpers";

export type FileType = "json" | "csv" | "pdf" | "xlsx";

export type RunExportFn = (
  fileType: FileType,
  exportFn: (rows: ExportRow[]) => void | Promise<void>,
  successMessage: string,
  errorMessage: string,
) => Promise<void>;

interface CreateStandardTableExportersArgs {
  runExport: RunExportFn;
  columns: ExportColumn[];
  filenameBase: string;
  title: string;
  subtitle?: string;
}

export interface StandardTableExporters {
  onExportJson: () => Promise<void>;
  onExportCsv: () => Promise<void>;
  onExportPdf: () => Promise<void>;
}

export default function createStandardTableExporters({
  runExport,
  columns,
  filenameBase,
  title,
  subtitle,
}: CreateStandardTableExportersArgs): StandardTableExporters {
  return {
    onExportJson: () =>
      runExport(
        "json",
        (rows) => exportTableJson({ rows, filename: `${filenameBase}.json` }),
        "JSON export started.",
        "Failed to export JSON",
      ),

    onExportCsv: () =>
      runExport(
        "csv",
        (rows) => exportTableCsv({ columns, rows, filename: `${filenameBase}.csv` }),
        "CSV export started.",
        "Failed to export CSV",
      ),

    onExportPdf: () =>
      runExport(
        "pdf",
        (rows) =>
          exportTablePdf({
            title,
            subtitle,
            columns,
            rows,
            filename: `${filenameBase}.pdf`,
          }),
        "PDF export started.",
        "Failed to export PDF",
      ),
  };
}
