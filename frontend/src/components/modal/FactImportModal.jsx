import { useMemo, useState } from "react";
import {
  Modal,
  Upload,
  Button,
  Typography,
  message,
  Alert,
  Progress,
  Space,
  Checkbox,
  Divider,
  Tag,
} from "antd";
import {
  InboxOutlined,
  UploadOutlined,
  ExperimentOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import { importFinancialFactsCsv } from "../../services/stock_service";
import { useAuthStore } from "../../store/useAuthStore";

const { Dragger } = Upload;
const { Text } = Typography;

const initialResult = null;

export default function ImportCsvModal({ open, onClose, onSuccess }) {
  const token = useAuthStore((state) => state.token);

  const [fileList, setFileList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadPercent, setUploadPercent] = useState(0);
  const [result, setResult] = useState(initialResult);
  const [dryRun, setDryRun] = useState(true);
  const [replaceAll, setReplaceAll] = useState(false);

  const selectedFile = fileList[0]?.originFileObj || null;

  const resultModeLabel = useMemo(() => {
    if (!result) return null;
    return result.dry_run ? "Dry Run" : "Import";
  }, [result]);

  const resetState = () => {
    setFileList([]);
    setLoading(false);
    setUploadPercent(0);
    setResult(initialResult);
    setDryRun(true);
    setReplaceAll(false);
  };

  const handleClose = () => {
    if (loading) return;
    resetState();
    onClose?.();
  };

  const handleUpload = async () => {
  if (!selectedFile) {
    message.warning("Please select a CSV file first.");
    return;
  }

  try {
    setLoading(true);
    setResult(null);
    setUploadPercent(0);

    console.log("🚀 Sending request...");
    console.log("👉 dryRun (frontend state):", dryRun);

    const response = await importFinancialFactsCsv(
      selectedFile,
      token,
      dryRun,
      replaceAll,
      (percent) => setUploadPercent(percent)
    );

    console.log("✅ Response received:");
    console.log("👉 response:", response);
    console.log("👉 response.dry_run:", response?.dry_run);

    setUploadPercent(100);
    setResult(response);

    if (response.dry_run) {
      message.success(response.message || "Dry run completed.");
    } else {
      message.success(response.message || "CSV imported successfully.");
      await onSuccess?.();
    }
  } catch (error) {
    console.error("❌ Upload error:", error);

    const detail =
      error?.response?.data?.detail ||
      error?.message ||
      "Import failed.";

    message.error(detail);

    setResult({
      message: "Import failed",
      dry_run: dryRun,
      inserted: 0,
      updated: 0,
      unchanged: 0,
      would_insert: 0,
      would_update: 0,
      would_unchanged: 0,
      skipped: 0,
      duplicates_in_file: 0,
      total_rows: 0,
      processed_rows: 0,
      errors: [detail],
    });
  } finally {
    setLoading(false);
  }
};

  const uploadProps = {
    multiple: false,
    accept: ".csv",
    beforeUpload: () => false,
    fileList,
    onChange: ({ fileList: newFileList }) => {
      setFileList(newFileList.slice(-1));
      setResult(null);
      setUploadPercent(0);
    },
    onRemove: () => {
      setFileList([]);
      setResult(null);
      setUploadPercent(0);
    },
  };

  return (
    <Modal
      title="Import Financial Facts CSV"
      open={open}
      onCancel={handleClose}
      destroyOnHidden
      width={720}
      footer={[
        <Button key="cancel" onClick={handleClose} disabled={loading}>
          Cancel
        </Button>,
        result && !result.dry_run && result.status !== "failed" ? (
          <Button key="close-success" danger onClick={handleClose}>
            Close
          </Button>
        ) : (
          <Button
            key="run"
            type="primary"
            icon={dryRun ? <ExperimentOutlined /> : <UploadOutlined />}
            loading={loading}
            onClick={handleUpload}
          >
            {dryRun ? "Run Dry Run" : "Import CSV"}
          </Button>
        ),
      ]}
    >
      <Space orientation="vertical" size={16} style={{ width: "100%" }}>
        <Dragger {...uploadProps}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">Click or drag CSV file to this area</p>
          <p className="ant-upload-hint">
            Required columns: stock_id, metric_id, statement_id, date_id, value
          </p>
        </Dragger>

        <Checkbox
          checked={dryRun}
          onChange={(e) => setDryRun(e.target.checked)}
          disabled={loading}
        >
          Dry run first (validate without writing to database)
        </Checkbox>

        <Checkbox
          checked={replaceAll}
          onChange={(e) => setReplaceAll(e.target.checked)}
          disabled={loading || dryRun}
        >
          Replace all existing rows
        </Checkbox>

        {selectedFile && (
          <Alert
            type="info"
            showIcon
            message="File selected"
            description={
              <div>
                <div>
                  <strong>Name:</strong> {selectedFile.name}
                </div>
                {selectedFile.size != null && (
                  <div>
                    <strong>Size:</strong>{" "}
                    {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                  </div>
                )}
              </div>
            }
          />
        )}

        {loading && (
          <div>
            <Text style={{ display: "block", marginBottom: 8 }}>
              {uploadPercent < 100
                ? "Uploading file..."
                : "Processing import on server..."}
            </Text>
            <Progress
              percent={uploadPercent}
              status="active"
              strokeColor={uploadPercent === 100 ? undefined : undefined}
            />
          </div>
        )}

        {result && (
          <>
            <Divider style={{ margin: 0 }} />
            <Alert
              type={result.errors?.length ? "warning" : "success"}
              showIcon
              icon={result.errors?.length ? undefined : <CheckCircleOutlined />}
              message={result.message || "Import result"}
              description={
                <Space orientation="vertical" size={12} style={{ width: "100%" }}>
                  <Space wrap>
                    <Tag color={result.dry_run ? "blue" : "green"}>
                      Mode: {resultModeLabel}
                    </Tag>
                    <Tag>Total rows: {result.total_rows ?? 0}</Tag>
                    <Tag>Processed rows: {result.processed_rows ?? 0}</Tag>
                    <Tag>Skipped: {result.skipped ?? 0}</Tag>
                    <Tag>Duplicates in file: {result.duplicates_in_file ?? 0}</Tag>
                  </Space>

                  {result.dry_run ? (
                    <Space wrap>
                      <Tag color="geekblue">
                        Would insert: {result.would_insert ?? 0}
                      </Tag>
                      <Tag color="purple">
                        Would update: {result.would_update ?? 0}
                      </Tag>
                      <Tag>
                        Would remain unchanged: {result.would_unchanged ?? 0}
                      </Tag>
                    </Space>
                  ) : (
                    <Space wrap>
                      <Tag color="green">Inserted: {result.inserted ?? 0}</Tag>
                      <Tag color="orange">Updated: {result.updated ?? 0}</Tag>
                      <Tag>Unchanged: {result.unchanged ?? 0}</Tag>
                    </Space>
                  )}

                  {result.errors?.length > 0 && (
                    <div>
                      <Text strong>Errors</Text>
                      <div
                        style={{
                          marginTop: 8,
                          maxHeight: 180,
                          overflow: "auto",
                          padding: 12,
                          border: "1px solid #f0f0f0",
                          borderRadius: 8,
                          background: "#fafafa",
                        }}
                      >
                        <ul style={{ margin: 0, paddingLeft: 18 }}>
                          {result.errors.map((err, idx) => (
                            <li key={idx}>{err}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}
                </Space>
              }
            />
          </>
        )}
      </Space>
    </Modal>
  );
}