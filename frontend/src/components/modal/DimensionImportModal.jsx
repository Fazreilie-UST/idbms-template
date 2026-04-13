import { useState } from "react";
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
} from "antd";
import {
  InboxOutlined,
  UploadOutlined,
  ExperimentOutlined,
} from "@ant-design/icons";
import { useAuthStore } from "../../store/useAuthStore";

const { Dragger } = Upload;
const { Text } = Typography;

export default function DimensionImportModal({
  open,
  onClose,
  onSuccess,
  title,
  importFn,
}) {
  const token = useAuthStore((state) => state.token);

  const [fileList, setFileList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploadPercent, setUploadPercent] = useState(0);
  const [result, setResult] = useState(null);
  const [dryRun, setDryRun] = useState(true);
  const [replaceAll, setReplaceAll] = useState(false);

  const selectedFile = fileList[0]?.originFileObj || null;

  const resetState = () => {
    setFileList([]);
    setLoading(false);
    setUploadPercent(0);
    setResult(null);
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

      const response = await importFn(
        selectedFile,
        token,
        dryRun,
        replaceAll,
        (percent) => setUploadPercent(percent)
      );

      setUploadPercent(100);
      setResult(response);

      if (response.dry_run) {
        message.success("Dry run completed.");
      } else {
        message.success("Import completed.");
        await onSuccess?.();
      }
    } catch (error) {
      const detail =
        error?.response?.data?.detail || error?.message || "Import failed.";
      message.error(detail);
      setResult({
        message: "Import failed",
        dry_run: dryRun,
        status: "failed",
        errors: [detail],
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={title}
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
        <Dragger
          multiple={false}
          accept=".csv"
          beforeUpload={() => false}
          fileList={fileList}
          onChange={({ fileList: newFileList }) => {
            setFileList(newFileList.slice(-1));
            setResult(null);
            setUploadPercent(0);
          }}
          onRemove={() => {
            setFileList([]);
            setResult(null);
            setUploadPercent(0);
          }}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">Click or drag CSV file to this area</p>
        </Dragger>

        <Checkbox checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} disabled={loading}>
          Dry run first
        </Checkbox>

        {/* <Checkbox
          checked={replaceAll}
          onChange={(e) => setReplaceAll(e.target.checked)}
          disabled={loading || dryRun}
        >
          Replace all existing rows
        </Checkbox> */}

        {loading && (
          <div>
            <Text style={{ display: "block", marginBottom: 8 }}>
              {uploadPercent < 100 ? "Uploading file..." : "Processing import on server..."}
            </Text>
            <Progress percent={uploadPercent} status="active" />
          </div>
        )}

        {result && (
          <Alert
            type={result.errors?.length ? "warning" : "success"}
            showIcon
            message={result.message}
            description={
              <div>
                <div>Status: {result.status || "completed"}</div>
                <div>Table: {result.table_name || "-"}</div>
                <div>File: {result.filename || "-"}</div>
                <div>Dry run: {String(result.dry_run)}</div>
                <div>Replace all: {String(result.replace_all)}</div>
                <div>Inserted: {result.inserted ?? 0}</div>
                <div>Updated: {result.updated ?? 0}</div>
                <div>Unchanged: {result.unchanged ?? 0}</div>
                <div>Would insert: {result.would_insert ?? 0}</div>
                <div>Would update: {result.would_update ?? 0}</div>
                <div>Would unchanged: {result.would_unchanged ?? 0}</div>
                <div>Skipped: {result.skipped ?? 0}</div>
                <div>Duplicates in file: {result.duplicates_in_file ?? 0}</div>
                <div>Total rows: {result.total_rows ?? 0}</div>
                <div>Processed rows: {result.processed_rows ?? 0}</div>

                {result.validation_summary && (
                  <div style={{ marginTop: 8 }}>
                    <strong>Validation Summary</strong>
                    <pre style={{ whiteSpace: "pre-wrap" }}>
                      {JSON.stringify(result.validation_summary, null, 2)}
                    </pre>
                  </div>
                )}

                {result.errors?.length > 0 && (
                  <ul style={{ marginTop: 8, paddingLeft: 20, maxHeight: 160, overflow: "auto" }}>
                    {result.errors.map((err, idx) => (
                      <li key={idx}>{err}</li>
                    ))}
                  </ul>
                )}
              </div>
            }
          />
        )}
      </Space>
    </Modal>
  );
}