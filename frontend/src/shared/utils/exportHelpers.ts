/**
 * Generic helpers for client-side export of table data.
 *
 * The `columns` array follows AntD's Table column shape (we only read
 * `title`, `key`, and `dataIndex`). `dataIndex` is treated as a top-level
 * key on each row.
 */

export interface ExportColumn {
  /** Column header — used for CSV header row and JSON keys. */
  title?: unknown;
  /** Fallback key when `title` is not a string. */
  key?: string;
  /** Property name to read from each row. */
  dataIndex: string;
}

export type ExportRow = Record<string, unknown>;

interface DownloadBlobOptions {
  content: BlobPart;
  filename: string;
  mimeType: string;
}

export function downloadBlob({ content, filename, mimeType }: DownloadBlobOptions): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
}

export function sanitizeExportValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  return String(value);
}

export function mapRowsByColumns(
  columns: ExportColumn[],
  rows: ExportRow[],
): Record<string, unknown>[] {
  return rows.map((row) => {
    const item: Record<string, unknown> = {};

    columns.forEach((col) => {
      const header = typeof col.title === "string" ? col.title : col.key ?? col.dataIndex;
      item[header] = row[col.dataIndex];
    });

    return item;
  });
}

export function buildCsv(rows: unknown[][]): string {
  return rows
    .map((row) =>
      row
        .map((cell) => {
          const escaped = sanitizeExportValue(cell).replace(/"/g, '""');
          return `"${escaped}"`;
        })
        .join(","),
    )
    .join("\n");
}
