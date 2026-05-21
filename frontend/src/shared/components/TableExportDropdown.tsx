import { Button, Dropdown, message } from "antd";
import { DownloadOutlined, LoadingOutlined } from "@ant-design/icons";

interface TableExportDropdownProps {
  disabled?: boolean;
  loading?: boolean;
  onExportJson?: () => void | Promise<void>;
  onExportCsv?: () => void | Promise<void>;
  onExportPdf?: () => void | Promise<void>;
}

export default function TableExportDropdown({
  disabled = false,
  loading = false,
  onExportJson,
  onExportCsv,
  onExportPdf,
}: TableExportDropdownProps) {
  const handleExport = (handler?: () => void | Promise<void>) => {
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
    <Dropdown menu={{ items }} trigger={["click"]} disabled={disabled || loading}>
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
