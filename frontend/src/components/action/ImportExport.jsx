import { Button, Space } from "antd";
import { UploadOutlined } from "@ant-design/icons";
import TableExportDropdown from "../dropdown/TableExportDropdown";

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
}) {
  return (
    <Space
      style={{
        marginBottom: 16,
        width: "100%",
        justifyContent: align === "start" ? "flex-start" : "flex-end",
      }}
    >
      {showImport && (
        <Button
          type="secondary"
          icon={<UploadOutlined />}
          onClick={onImport}
        >
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