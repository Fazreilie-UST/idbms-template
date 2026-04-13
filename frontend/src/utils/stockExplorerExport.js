import { jsPDF } from "jspdf";
import { autoTable } from "jspdf-autotable";

export function exportStockExplorerJson({ summary, dateColumns, rows }) {
  const payload = {
    summary,
    columns: ["Metric", ...dateColumns],
    rows,
  };

  downloadBlob({
    content: JSON.stringify(payload, null, 2),
    filename: buildExportFilename(summary, "json"),
    mimeType: "application/json",
  });
}

export function exportStockExplorerCsv({ summary, dateColumns, rows }) {
  const csv = buildCsv([
    ["Metric", ...dateColumns],
    ...rows.map((row) => [
      row.metric_name,
      ...dateColumns.map((dateKey) => row[dateKey] ?? ""),
    ]),
  ]);

  downloadBlob({
    content: csv,
    filename: buildExportFilename(summary, "csv"),
    mimeType: "text/csv;charset=utf-8;",
  });
}

export function exportStockExplorerPdf({ summary, dateColumns, rows }) {
  const doc = new jsPDF({
    orientation: dateColumns.length > 4 ? "landscape" : "portrait",
    unit: "pt",
    format: "a4",
  });

  const title = "Stock Statement Explorer";
  const stockLabel = summary?.stock_code
    ? `${summary.stock_code}${summary?.stock_name ? ` - ${summary.stock_name}` : ""}`
    : "-";
  const statementLabel = summary?.statement_name || "-";

  doc.setFontSize(16);
  doc.setFont("helvetica", "bold");
  doc.text(title, 40, 40);

  doc.setFontSize(10);
  doc.setFont("helvetica", "normal");
  doc.text(`Stock: ${stockLabel}`, 40, 62);
  doc.text(`Statement: ${statementLabel}`, 40, 78);

  autoTable(doc, {
    startY: 96,
    head: [["Metric", ...dateColumns]],
    body: rows.map((row) => [
      row.metric_name,
      ...dateColumns.map((dateKey) => row[dateKey] ?? "-"),
    ]),
    styles: {
      fontSize: 8,
      cellPadding: 6,
      overflow: "linebreak",
      lineColor: [225, 230, 235],
      lineWidth: 0.5,
      textColor: [45, 55, 72],
      valign: "middle",
    },
    headStyles: {
      fontStyle: "bold",
      fillColor: [41, 98, 255],
      textColor: [255, 255, 255],
      halign: "center",
    },
    alternateRowStyles: {
      fillColor: [250, 250, 252],
    },
    columnStyles: {
      0: { cellWidth: 240, halign: "left" },
    },
    margin: { top: 40, left: 40, right: 40, bottom: 40 },

    didParseCell: function (data) {
      if (data.section !== "body") return;

      const row = rows[data.row.index];
      const depth = row.depth || 0;
      const isParent = !!row.is_parent;

      if (data.column.index === 0) {
        // Add visible indentation for children
        data.cell.styles.cellPadding = {
          top: 6,
          right: 6,
          bottom: 6,
          left: 10 + depth * 14,
        };

        // Parent-child visual marker
        data.cell.text = [
          `${depth > 0 ? "> " : ""}${row.metric_name || "-"}`
        ];
      }

      if (isParent) {
        data.cell.styles.fontStyle = "bold";
        data.cell.styles.fillColor = [232, 240, 254]; // soft blue for parents
        data.cell.styles.textColor = [25, 55, 109];
      } else {
        data.cell.styles.fillColor = [248, 250, 252]; // very light gray for children
        data.cell.styles.textColor = [55, 65, 81];
      }
    },
  });

  doc.save(buildExportFilename(summary, "pdf"));
}

function buildCsv(rows) {
  return rows
    .map((row) =>
      row
        .map((cell) => {
          const value = cell ?? "";
          const escaped = String(value).replace(/"/g, '""');
          return `"${escaped}"`;
        })
        .join(",")
    )
    .join("\n");
}

function downloadBlob({ content, filename, mimeType }) {
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

function buildExportFilename(summary, extension) {
  const stock = summary?.stock_code || "stock";
  const statement = (summary?.statement_name || "statement")
    .replace(/\s+/g, "_")
    .toLowerCase();

  return `${stock}_${statement}.${extension}`;
}