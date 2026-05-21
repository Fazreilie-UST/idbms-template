import {
  buildCsv,
  downloadBlob,
  mapRowsByColumns,
  sanitizeExportValue,
  type ExportColumn,
  type ExportRow,
} from "@/shared/utils/exportHelpers";

interface ExportTableJsonArgs {
  rows: ExportRow[];
  filename: string;
}

export function exportTableJson({ rows, filename }: ExportTableJsonArgs): void {
  downloadBlob({
    content: JSON.stringify(rows, null, 2),
    filename,
    mimeType: "application/json",
  });
}

interface ExportTableCsvArgs {
  columns: ExportColumn[];
  rows: ExportRow[];
  filename: string;
}

export function exportTableCsv({ columns, rows, filename }: ExportTableCsvArgs): void {
  const mappedRows = mapRowsByColumns(columns, rows);

  const headers = Object.keys(mappedRows[0] ?? {});
  const csvRows: unknown[][] = [
    headers,
    ...mappedRows.map((row) => headers.map((header) => sanitizeExportValue(row[header]))),
  ];

  downloadBlob({
    content: buildCsv(csvRows),
    filename,
    mimeType: "text/csv;charset=utf-8;",
  });
}
