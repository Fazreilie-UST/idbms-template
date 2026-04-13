import { Button, Dropdown, message } from "antd";
import { DownloadOutlined, LoadingOutlined } from "@ant-design/icons";

export default function TableExportDropdown({
  disabled = false,
  loading = false,
  onExportJson,
  onExportCsv,
  onExportPdf,
}) {
  const handleExport = (handler) => {
    if (disabled) {
      message.warning("No data available to export.");
      return;
    }

    if (loading) {
      return;
    }

    handler?.();
  };

  const items = [
    {
      key: "json",
      label: "JSON",
      disabled: disabled || loading,
      onClick: () => handleExport(onExportJson),
    },
    {
      key: "csv",
      label: "CSV",
      disabled: disabled || loading,
      onClick: () => handleExport(onExportCsv),
    },
    {
      key: "pdf",
      label: "PDF",
      disabled: disabled || loading,
      onClick: () => handleExport(onExportPdf),
    },
  ];

  return (
    <Dropdown
      menu={{ items }}
      trigger={["click"]}
      disabled={disabled || loading}
    >
      <Button
        type="primary"
        icon={loading ? <LoadingOutlined /> : <DownloadOutlined />}
        loading={loading}
        disabled={disabled || loading}
      >
        Download
      </Button>
    </Dropdown>
  );
}