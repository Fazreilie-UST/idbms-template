import { exportTableJson, exportTableCsv } from "./tableDataExport";
import { exportTablePdf } from "./tablePdfExport";

export default function createStandardTableExporters({
  runExport,
  columns,
  filenameBase,
  title,
  subtitle,
}) {
  return {
    onExportJson: () =>
      runExport(
        "json",
        (rows) =>
          exportTableJson({
            rows,
            filename: `${filenameBase}.json`,
          }),
        "JSON export started.",
        "Failed to export JSON"
      ),

    onExportCsv: () =>
      runExport(
        "csv",
        (rows) =>
          exportTableCsv({
            columns,
            rows,
            filename: `${filenameBase}.csv`,
          }),
        "CSV export started.",
        "Failed to export CSV"
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
        "Failed to export PDF"
      ),
  };
}