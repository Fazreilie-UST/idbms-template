import { Button, Dropdown, message } from "antd";
import { DownloadOutlined } from "@ant-design/icons";

export default function ExportDropdown({
  disabled = false,
  onExportJson,
  onExportCsv,
  onExportPdf,
}) {
  const items = [
    {
      key: "json",
      label: "JSON",
      disabled,
      onClick: () => {
        if (disabled) {
          message.warning("No data available to export.");
          return;
        }
        onExportJson?.();
      },
    },
    {
      key: "csv",
      label: "CSV",
      disabled,
      onClick: () => {
        if (disabled) {
          message.warning("No data available to export.");
          return;
        }
        onExportCsv?.();
      },
    },
    {
      key: "pdf",
      label: "PDF",
      disabled,
      onClick: () => {
        if (disabled) {
          message.warning("No data available to export.");
          return;
        }
        onExportPdf?.();
      },
    },
  ];

  return (
    <Dropdown menu={{ items }} trigger={["click"]}>
      <Button type="primary" icon={<DownloadOutlined />} disabled={disabled}>
        Download
      </Button>
    </Dropdown>
  );
}