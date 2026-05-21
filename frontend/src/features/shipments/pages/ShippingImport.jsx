import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Modal,
  Popconfirm,
  Progress,
  Space,
  Spin,
  Table,
  Tag,
  Tooltip,
  Typography,
  Upload,
  message,
} from "antd";
import {
  DeleteOutlined,
  EyeOutlined,
  InboxOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";

import {
  deleteShippingImport,
  listShippingImports,
  streamProcessShippingImport,
  uploadShippingImportFile,
} from "@/features/shipments/services/shipping_import_service";

const { Title, Paragraph, Text } = Typography;
const { Dragger } = Upload;

const STATUS_COLORS = {
  pending: "default",
  processing: "processing",
  success: "success",
  failed: "error",
  skipped: "warning",
};

const PROCESSABLE = new Set(["pending", "failed"]);

function formatBytes(bytes) {
  if (!bytes && bytes !== 0) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

export default function ShippingImport() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });
  const [uploading, setUploading] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);
  const [detail, setDetail] = useState(null);

  // In-flight processing state (local; one batch at a time).
  const [processing, setProcessing] = useState(false);
  const [progress, setProgress] = useState(null);
  const [rowOverrides, setRowOverrides] = useState({});

  const loadData = useCallback(
    async (page = pagination.current, pageSize = pagination.pageSize) => {
      setLoading(true);
      try {
        const data = await listShippingImports({ page, pageSize });
        setRows(data.items || []);
        setPagination({
          current: data.page,
          pageSize: data.page_size,
          total: data.total,
        });
      } catch (err) {
        message.error(`Failed to load imports: ${err.message}`);
      } finally {
        setLoading(false);
      }
    },
    [pagination.current, pagination.pageSize],
  );

  useEffect(() => {
    loadData(1, pagination.pageSize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleUpload = async (file) => {
    setUploading(true);
    try {
      const result = await uploadShippingImportFile(file, { autoProcess: false });
      const record = result?.record || result;
      if (result?.duplicate) {
        Modal.warning({
          title: "Duplicate file detected",
          content: (
            <div>
              <p>
                <Text strong>{file.name}</Text> has the exact same contents as a
                previously uploaded file:
              </p>
              <ul style={{ marginBottom: 0 }}>
                <li>Existing file: <Text code>{record.original_filename}</Text></li>
                <li>Status: <Tag color={STATUS_COLORS[record.status]}>{record.status}</Tag></li>
                <li>Uploaded: {formatDate(record.created_at)}</li>
              </ul>
              <p style={{ marginTop: 12, marginBottom: 0 }}>
                The new upload was discarded. Use the existing file in the list
                if you want to (re)process it.
              </p>
            </div>
          ),
        });
      } else {
        message.success(`Stored "${file.name}". Select it below and click Process to import.`);
      }
      await loadData(1, pagination.pageSize);
    } catch (err) {
      message.error(`Upload failed: ${err.message}`);
    } finally {
      setUploading(false);
    }
    return false; // prevent antd auto-upload
  };

  const handleDelete = async (id) => {
    try {
      await deleteShippingImport(id);
      message.success("Deleted");
      setSelectedIds((s) => s.filter((x) => x !== id));
      await loadData();
    } catch (err) {
      message.error(`Delete failed: ${err.message}`);
    }
  };

  const runStream = useCallback(async (ids) => {
    if (!ids.length) {
      message.info("No files to process");
      return;
    }
    if (processing) {
      message.info("A batch is already in progress");
      return;
    }
    setProcessing(true);
    setProgress({
      mode: "process",
      totalRows: 0,
      doneRows: 0,
      files: ids.length,
      fileIndex: 0,
      currentId: null,
      currentName: "",
      currentTotal: 0,
      currentDone: 0,
      succeededFiles: 0,
      failedFiles: 0,
      lastConfig: "",
    });
    setSelectedIds(ids);

    for (let i = 0; i < ids.length; i += 1) {
      const id = ids[i];
      const row = rows.find((r) => r.id === id);
      setProgress((p) => ({
        ...(p || {}),
        fileIndex: i + 1,
        currentId: id,
        currentName: row?.original_filename || `#${id}`,
        currentTotal: 0,
        currentDone: 0,
      }));
      setRowOverrides((o) => ({ ...o, [id]: { status: "processing" } }));

      try {
        const last = await streamProcessShippingImport(id, (evt) => {
          if (evt.event === "init") {
            setProgress((p) => ({
              ...(p || {}),
              currentTotal: evt.total || 0,
              totalRows: (p?.totalRows || 0) + (evt.total || 0),
            }));
          } else if (evt.event === "row_done" || evt.event === "row_skipped") {
            setProgress((p) => ({
              ...(p || {}),
              currentDone: evt.processed,
              doneRows: (p?.doneRows || 0) + 1,
              lastConfig: evt.config_number || p?.lastConfig || "",
            }));
          } else if (evt.event === "complete") {
            setRowOverrides((o) => ({ ...o, [id]: evt.record }));
          } else if (evt.event === "error") {
            setRowOverrides((o) => ({
              ...o,
              [id]: { status: "failed", error_message: evt.message },
            }));
          }
        });
        if (last?.event === "complete" && last.record?.status === "success") {
          setProgress((p) => ({
            ...(p || {}),
            succeededFiles: (p?.succeededFiles || 0) + 1,
          }));
        } else {
          setProgress((p) => ({
            ...(p || {}),
            failedFiles: (p?.failedFiles || 0) + 1,
          }));
        }
      } catch (err) {
        message.error(`Processing failed for "${row?.original_filename || id}": ${err.message}`);
        setRowOverrides((o) => ({
          ...o,
          [id]: { status: "failed", error_message: err.message },
        }));
        setProgress((p) => ({
          ...(p || {}),
          failedFiles: (p?.failedFiles || 0) + 1,
        }));
      }
    }

    await loadData();
    setRowOverrides({});
    setProcessing(false);
    // narrow selection to anything still failed so the user can retry quickly
    setSelectedIds((sel) => sel.filter((id) => {
      const r = rows.find((x) => x.id === id);
      return r && r.status === "failed";
    }));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [processing, rows]);

  const handleReprocess = (id) => runStream([id]);

  const displayRows = useMemo(() => {
    if (!Object.keys(rowOverrides).length) return rows;
    return rows.map((r) =>
      rowOverrides[r.id] ? { ...r, ...rowOverrides[r.id] } : r,
    );
  }, [rows, rowOverrides]);

  const processableSelected = useMemo(
    () => selectedIds.filter((id) => {
      const row = displayRows.find((r) => r.id === id);
      return row && PROCESSABLE.has(row.status);
    }),
    [selectedIds, displayRows],
  );

  const allPendingIds = useMemo(
    () => displayRows.filter((r) => PROCESSABLE.has(r.status)).map((r) => r.id),
    [displayRows],
  );

  const columns = useMemo(
    () => [
      {
        title: "File",
        dataIndex: "original_filename",
        key: "original_filename",
        sorter: (a, b) =>
          (a.original_filename || "").localeCompare(
            b.original_filename || "",
            undefined,
            { numeric: true, sensitivity: "base" },
          ),
        render: (text, record) => (
          <Space orientation="vertical" size={0}>
            <Text strong>{text}</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {formatBytes(record.file_size)}
            </Text>
          </Space>
        ),
      },
      {
        title: "Status",
        dataIndex: "status",
        key: "status",
        width: 160,
        render: (s) => {
          if (s === "processing") {
            return (
              <Space size={6}>
                <Spin size="small" />
                <Tag color={STATUS_COLORS.processing}>processing</Tag>
              </Space>
            );
          }
          return <Tag color={STATUS_COLORS[s] || "default"}>{s}</Tag>;
        },
      },
      {
        title: "Inserted",
        key: "inserted",
        width: 100,
        render: (_, r) =>
          r.summary?.inserted != null ? r.summary.inserted : "—",
      },
      {
        title: "Duplicates",
        key: "dup",
        width: 110,
        render: (_, r) =>
          r.summary?.skipped_duplicate != null
            ? r.summary.skipped_duplicate
            : "—",
      },
      {
        title: "Uploaded By",
        key: "uploaded_by",
        render: (_, r) => r.uploaded_by?.full_name || r.uploaded_by?.email || "—",
      },
      {
        title: "Uploaded At",
        dataIndex: "created_at",
        key: "created_at",
        render: formatDate,
      },
      {
        title: "Processed At",
        dataIndex: "processed_at",
        key: "processed_at",
        render: formatDate,
      },
      {
        title: "Actions",
        key: "actions",
        width: 160,
        render: (_, record) => (
          <Space>
            <Tooltip title="View details">
              <Button
                size="small"
                icon={<EyeOutlined />}
                onClick={() => setDetail(record)}
              />
            </Tooltip>
            <Tooltip title={PROCESSABLE.has(record.status) ? "Process" : "Reprocess"}>
              <Button
                size="small"
                icon={<ReloadOutlined />}
                disabled={processing || record.status === "processing"}
                onClick={() => handleReprocess(record.id)}
              />
            </Tooltip>
            <Popconfirm
              title="Delete this import file?"
              description="The file on disk will also be removed."
              onConfirm={() => handleDelete(record.id)}
              okText="Delete"
              okButtonProps={{ danger: true }}
            >
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </Space>
        ),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [processing],
  );

  return (
    <Space orientation="vertical" size="large" style={{ width: "100%" }}>
      <div>
        <Title level={3} style={{ marginBottom: 0 }}>
          Import Shipments
        </Title>
        <Paragraph type="secondary" style={{ marginTop: 4 }}>
          Drag and drop shipping Excel files (Master Board Tracker layout).
          Files are stored on the server and listed below in{" "}
          <Text code>pending</Text> state.{" "}
          <Text strong>Nothing is written to the database</Text> until you
          select one or more rows and click <Text code>Process</Text>. Files
          with the exact same contents as an earlier upload are detected and
          skipped automatically.
        </Paragraph>
      </div>

      <Card>
        <Dragger
          name="file"
          multiple
          accept=".xlsx,.xls"
          showUploadList={false}
          beforeUpload={handleUpload}
          disabled={uploading}
        >
          <p className="ant-upload-drag-icon">
            <InboxOutlined />
          </p>
          <p className="ant-upload-text">
            Click or drag shipping files to this area to upload
          </p>
          <p className="ant-upload-hint">
            Supports a single or bulk upload. .xlsx files only. Max 50 MB per file.
          </p>
        </Dragger>
      </Card>

      <Card
        title="Uploaded files"
        extra={
          <Space>
            <Button
              icon={<PlayCircleOutlined />}
              type="primary"
              loading={processing}
              disabled={!processableSelected.length || processing}
              onClick={() => runStream(processableSelected)}
            >
              Process Selected ({processableSelected.length})
            </Button>
            <Popconfirm
              title="Process all pending and failed files?"
              onConfirm={() => runStream(allPendingIds)}
              disabled={!allPendingIds.length || processing}
            >
              <Button
                icon={<ThunderboltOutlined />}
                loading={processing}
                disabled={!allPendingIds.length || processing}
              >
                Process All ({allPendingIds.length})
              </Button>
            </Popconfirm>
            <Button onClick={() => loadData()} icon={<ReloadOutlined />} disabled={processing}>
              Refresh
            </Button>
          </Space>
        }
      >
        {progress && (
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 12 }}
            message={
              <Space orientation="vertical" size={6} style={{ width: "100%" }}>
                <Text strong>
                  Processing row {progress.doneRows} / {progress.totalRows || "?"}
                  {" · "}File {progress.fileIndex} of {progress.files}
                  {progress.currentName ? ` — ${progress.currentName}` : ""}
                </Text>
                <Progress
                  percent={
                    progress.totalRows > 0
                      ? Math.min(
                          100,
                          Math.round((progress.doneRows / progress.totalRows) * 100),
                        )
                      : 0
                  }
                  status={
                    progress.failedFiles > 0
                      ? "exception"
                      : progress.doneRows >= progress.totalRows && progress.totalRows > 0
                      ? "success"
                      : "active"
                  }
                  size="small"
                />
                {progress.currentTotal > 0 && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Current file: {progress.currentDone} / {progress.currentTotal} rows
                    {progress.lastConfig ? ` · last: ${progress.lastConfig}` : ""}
                  </Text>
                )}
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Files: {progress.succeededFiles} succeeded · {progress.failedFiles} failed
                </Text>
              </Space>
            }
          />
        )}
        <Table
          rowKey="id"
          loading={loading}
          dataSource={displayRows}
          columns={columns}
          expandable={{
            rowExpandable: (r) => Boolean(r.error_message) || Boolean(r.summary),
            expandedRowRender: (r) => (
              <Space orientation="vertical" size={8} style={{ width: "100%" }}>
                {r.error_message && (
                  <Alert
                    type="error"
                    showIcon
                    message={`Error processing ${r.original_filename}`}
                    description={
                      <pre
                        style={{
                          margin: 0,
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                          fontSize: 12,
                          fontFamily:
                            "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace",
                        }}
                      >
                        {r.error_message}
                      </pre>
                    }
                  />
                )}
                {r.summary && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {r.summary.inserted ?? 0} inserted ·{" "}
                    {r.summary.skipped_duplicate ?? 0} duplicate(s) ·{" "}
                    {r.summary.missing_user ?? 0} missing user(s) ·{" "}
                    {r.summary.sheets_processed ?? 0} sheet(s) processed
                    {(r.summary.sheets_skipped || []).length > 0 && (
                      <> · sheets skipped: {(r.summary.sheets_skipped || []).join(", ")}</>
                    )}
                  </Text>
                )}
              </Space>
            ),
          }}
          rowSelection={{
            selectedRowKeys: selectedIds,
            onChange: (keys) => setSelectedIds(keys),
            getCheckboxProps: (record) => ({
              name: record.original_filename,
            }),
          }}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
            onChange: (page, size) => loadData(page, size),
          }}
        />
      </Card>

      <Modal
        open={!!detail}
        onCancel={() => setDetail(null)}
        footer={null}
        width={720}
        title={detail?.original_filename || "Import details"}
      >
        {detail && (
          <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
            <div>
              <Tag color={STATUS_COLORS[detail.status] || "default"}>
                {detail.status}
              </Tag>
              <Text type="secondary" style={{ marginLeft: 8 }}>
                Uploaded {formatDate(detail.created_at)}
                {detail.processed_at && ` · Processed ${formatDate(detail.processed_at)}`}
              </Text>
            </div>

            {detail.error_message && (
              <Alert type="error" message="Error" description={detail.error_message} />
            )}

            {detail.summary && (
              <Card size="small" title="Parse summary">
                <Space orientation="vertical" size={4} style={{ width: "100%" }}>
                  <Text>
                    <strong>Inserted:</strong> {detail.summary.inserted ?? 0}
                  </Text>
                  <Text>
                    <strong>Skipped (duplicates):</strong>{" "}
                    {detail.summary.skipped_duplicate ?? 0}
                  </Text>
                  <Text>
                    <strong>Missing user references:</strong>{" "}
                    {detail.summary.missing_user ?? 0}
                  </Text>
                  <Text>
                    <strong>Sheets processed:</strong>{" "}
                    {detail.summary.sheets_processed ?? 0}
                  </Text>
                  <Text>
                    <strong>Sheets skipped:</strong>{" "}
                    {(detail.summary.sheets_skipped || []).join(", ") || "—"}
                  </Text>
                  {(detail.summary.missing_recipients || []).length > 0 && (
                    <Alert
                      type="warning"
                      message={`${detail.summary.missing_recipients.length} unresolved recipient name(s)`}
                      description={
                        <ul style={{ marginBottom: 0 }}>
                          {detail.summary.missing_recipients.map((n) => (
                            <li key={n}>{n}</li>
                          ))}
                        </ul>
                      }
                    />
                  )}
                </Space>
              </Card>
            )}
          </Space>
        )}
      </Modal>
    </Space>
  );
}
