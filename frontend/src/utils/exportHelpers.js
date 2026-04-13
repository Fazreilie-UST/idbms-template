export function downloadBlob({ content, filename, mimeType }) {
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

export function sanitizeExportValue(value) {
  if (value === null || value === undefined) return "";
  return String(value);
}

export function mapRowsByColumns(columns, rows) {
  return rows.map((row) => {
    const item = {};

    columns.forEach((col) => {
      const header = typeof col.title === "string" ? col.title : col.key;
      item[header] = row[col.dataIndex];
    });

    return item;
  });
}

export function buildCsv(rows) {
  return rows
    .map((row) =>
      row
        .map((cell) => {
          const escaped = sanitizeExportValue(cell).replace(/"/g, '""');
          return `"${escaped}"`;
        })
        .join(",")
    )
    .join("\n");
}