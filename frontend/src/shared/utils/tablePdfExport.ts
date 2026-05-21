import { jsPDF } from "jspdf";
import { autoTable } from "jspdf-autotable";

import type { ExportColumn, ExportRow } from "@/shared/utils/exportHelpers";

interface ExportTablePdfArgs {
  title: string;
  subtitle?: string;
  columns: ExportColumn[];
  rows: ExportRow[];
  filename: string;
}

export function exportTablePdf({
  title,
  subtitle,
  columns,
  rows,
  filename,
}: ExportTablePdfArgs): void {
  const doc = new jsPDF({
    orientation: columns.length > 5 ? "landscape" : "portrait",
    unit: "pt",
    format: "a4",
  });

  doc.setFontSize(16);
  doc.text(title, 40, 40);

  if (subtitle) {
    doc.setFontSize(10);
    doc.text(subtitle, 40, 60);
  }

  autoTable(doc, {
    startY: subtitle ? 76 : 60,
    head: [columns.map((col) => (typeof col.title === "string" ? col.title : col.key ?? col.dataIndex))],
    body: rows.map((row) =>
      columns.map((col) => {
        const value = row[col.dataIndex];
        return value === null || value === undefined || value === "" ? "-" : String(value);
      }),
    ),
    styles: {
      fontSize: 8,
      cellPadding: 6,
      overflow: "linebreak",
      lineWidth: 0.4,
    },
    headStyles: {
      fontStyle: "bold",
    },
    margin: { top: 40, left: 40, right: 40, bottom: 40 },
  });

  doc.save(filename);
}
