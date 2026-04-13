import { buildCsv, downloadBlob, mapRowsByColumns, sanitizeExportValue } from "./exportHelpers";

export function exportTableJson({ rows, filename }) {
  downloadBlob({
    content: JSON.stringify(rows, null, 2),
    filename,
    mimeType: "application/json",
  });
}

export function exportTableCsv({ columns, rows, filename }) {
  const mappedRows = mapRowsByColumns(columns, rows);

  const headers = Object.keys(mappedRows[0] || {});
  const csvRows = [
    headers,
    ...mappedRows.map((row) => headers.map((header) => sanitizeExportValue(row[header]))),
  ];

  downloadBlob({
    content: buildCsv(csvRows),
    filename,
    mimeType: "text/csv;charset=utf-8;",
  });
}