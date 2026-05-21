import { Button, Space } from "antd";
import { UploadOutlined } from "@ant-design/icons";
import TableExportDropdown from "@/shared/components/TableExportDropdown";

interface TablePageActionsProps {
  importLabel?: string;
  onImport?: () => void;
  showImport?: boolean;
  exporting?: boolean;
  exportDisabled?: boolean;
  onExportJson?: () => void | Promise<void>;
  onExportCsv?: () => void | Promise<void>;
  onExportPdf?: () => void | Promise<void>;
  align?: "start" | "end";
}

export default function TablePageActions({
  importLabel = "Add Data",
  onImport,
  showImport = true,
  exporting = false,
  exportDisabled = false,
  onExportJson,
  onExportCsv,
  onExportPdf,
  align = "end",
}: TablePageActionsProps) {
  return (
    <Space
      style={{
        marginBottom: 16,
        width: "100%",
        justifyContent: align === "start" ? "flex-start" : "flex-end",
      }}
    >
      {showImport && (
        <Button icon={<UploadOutlined />} onClick={onImport}>
          {importLabel}
        </Button>
      )}

      <TableExportDropdown
        loading={exporting}
        disabled={exportDisabled}
        onExportJson={onExportJson}
        onExportCsv={onExportCsv}
        onExportPdf={onExportPdf}
      />
    </Space>
  );
}
