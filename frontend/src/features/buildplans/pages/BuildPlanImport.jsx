import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Form,
  InputNumber,
  Modal,
  Popconfirm,
  Progress,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
  Upload,
  message,
} from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  InboxOutlined,
  PlayCircleOutlined,
  ReloadOutlined,
  ThunderboltOutlined,
} from "@ant-design/icons";

import {
  deleteBuildPlanImport,
  getImportShippingInfos,
  getImportSiRows,
  listBuildPlanImports,
  updateBuildPlanImportMetadata,
  uploadBuildPlanFile,
} from "@/features/buildplans/services/build_plan_import_service";
import { useBuildPlanImportStore } from "@/features/buildplans/store/useBuildPlanImportStore";
import { useAuthStore } from "@/shared/store/useAuthStore";
import {
  textSearchFilter,
  valueFilters,
} from "@/shared/utils/tableColumnHelpers";

const { Title, Paragraph, Text } = Typography;
const { Dragger } = Upload;

const STATUS_COLORS = {
  pending: "default",
  processing: "processing",
  success: "success",
  failed: "error",
  skipped: "warning",
};

const PROCESSABLE = new Set(["pending", "failed", "skipped"]);
const ALREADY_ATTEMPTED = new Set(["success", "failed", "skipped"]);

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

export default function BuildPlanImport() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 20, total: 0 });
  // Server-side sort: `column` maps to the backend's `sort_by` key, `order`
  // is the Ant Design value ("ascend" / "descend" / null).
  const [sort, setSort] = useState({ column: null, order: null });
  const [uploading, setUploading] = useState(false);
  const [selectedIds, setSelectedIds] = useState([]);
  const [detail, setDetail] = useState(null);
  const [editTarget, setEditTarget] = useState(null);
  const [editForm] = Form.useForm();
  // Which slice of files to show: every uploader's files ("all") or just the
  // ones the current user uploaded ("mine"). PMs can only *process* their own
  // files (enforced by the backend + canActOn below), so the "mine" tab gives
  // them a focused view; admins can switch freely.
  const [scope, setScope] = useState("all");

  // Current user is the gatekeeper for "only the uploader can process this
  // file". Admins bypass the check (matches the backend rule).
  const authUser = useAuthStore((s) => s.user);
  const currentUserId = authUser?.id ?? null;
  const currentRole =
    authUser?.role ||
    (Array.isArray(authUser?.roles) ? authUser.roles[0] : null) ||
    null;
  const isAdmin = currentRole === "Admin";

  const canActOn = useCallback(
    (record) => {
      if (isAdmin) return true;
      if (record?.uploaded_by?.id == null) return false;
      if (currentUserId == null) return false;
      return record.uploaded_by.id === currentUserId;
    },
    [isAdmin, currentUserId],
  );

  // Background batch run lives in a global store so the progress bar survives
  // page navigation. We still derive the table view + checklist from local
  // `rows`, but merge in any in-flight overrides published by the store.
  const processing = useBuildPlanImportStore((s) => s.processing);
  const progress = useBuildPlanImportStore((s) => s.progress);
  const rowOverrides = useBuildPlanImportStore((s) => s.rowOverrides);
  const activeIds = useBuildPlanImportStore((s) => s.activeIds);
  const lastRunCompletedAt = useBuildPlanImportStore((s) => s.lastRunCompletedAt);
  const startRun = useBuildPlanImportStore((s) => s.startRun);
  const clearOverrides = useBuildPlanImportStore((s) => s.clearOverrides);

  const loadData = useCallback(
    async (
      page = pagination.current,
      pageSize = pagination.pageSize,
      sortOverride,
      scopeOverride,
    ) => {
      setLoading(true);
      const s = sortOverride ?? sort;
      const sc = scopeOverride ?? scope;
      try {
        const data = await listBuildPlanImports({
          page,
          pageSize,
          sort_by: s.column || undefined,
          sort_order:
            s.order === "ascend"
              ? "asc"
              : s.order === "descend"
              ? "desc"
              : undefined,
          mine: sc === "mine" ? true : undefined,
        });
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
    [pagination.current, pagination.pageSize, sort, scope],
  );

  useEffect(() => {
    loadData(1, pagination.pageSize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Translate Ant's onChange(pagination, filters, sorter) into a server call.
  // Sorter can arrive as an array when multiple columns are sortable; we only
  // support single-column sort and just take the first entry.
  const handleTableChange = useCallback(
    (nextPagination, _filters, sorter) => {
      const s = Array.isArray(sorter) ? sorter[0] : sorter;
      const nextSort = {
        column: s && s.order ? s.columnKey || s.field : null,
        order: s && s.order ? s.order : null,
      };
      setSort(nextSort);
      loadData(
        nextPagination.current || 1,
        nextPagination.pageSize || pagination.pageSize,
        nextSort,
      );
    },
    [loadData, pagination.pageSize],
  );

  const handleUpload = async (file) => {
    setUploading(true);
    try {
      const result = await uploadBuildPlanFile(file, { autoProcess: false });
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

  const handleReprocess = async (id) => {
    // Route single-file reprocess through the streaming batch flow so the
    // progress bar shows up and the row gets the in-flight "processing"
    // override, identical to the toolbar's Process Selected.
    await handleProcess([id], { reprocess: true });
  };

  const openEdit = (record) => {
    editForm.setFieldsValue({
      work_week: record.work_week ?? null,
      work_year: record.work_year ?? null,
      file_revision: record.file_revision ?? null,
    });
    setEditTarget(record);
  };

  const handleEditSave = async () => {
    try {
      const values = await editForm.validateFields();
      const updated = await updateBuildPlanImportMetadata(editTarget.id, values);
      message.success("Metadata updated");
      setEditTarget(null);
      // Replace the row locally so the UI reflects the new WW/Year/Rev and
      // (if applicable) the reset-to-pending status without a full reload.
      setRows((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
    } catch (err) {
      if (err?.errorFields) return; // validation error already shown
      message.error(`Update failed: ${err.message}`);
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteBuildPlanImport(id);
      message.success("Deleted");
      setSelectedIds((s) => s.filter((x) => x !== id));
      await loadData();
    } catch (err) {
      message.error(`Delete failed: ${err.message}`);
    }
  };

  const handleProcess = async (ids, { reprocess, files } = {}) => {
    if (!ids.length) {
      message.info("No files selected");
      return;
    }
    if (processing) {
      message.info("A batch is already in progress");
      return;
    }
    // Auto-detect reprocess mode when the caller doesn't specify: if every
    // chosen file has already been attempted (success/failed/skipped) it's a
    // reprocess; otherwise treat as a first-time process.
    const mode =
      reprocess === true
        ? "reprocess"
        : reprocess === false
        ? "process"
        : ids.every((id) => {
            const row = displayRows.find((r) => r.id === id);
            return row && ALREADY_ATTEMPTED.has(row.status);
          })
        ? "reprocess"
        : "process";
    // Mirror the chosen ids in the checklist so it's obvious what's running.
    setSelectedIds(ids);
    try {
      // When the caller has loaded extra file metadata (e.g. Process-All
      // across pages), prefer that so the progress bar can show filenames
      // for rows not on the current pagination page.
      await startRun({ ids, files: files || rows, mode });
    } catch (err) {
      message.error(`Could not start batch: ${err.message}`);
    }
  };

  // "Process All (across pages)" — the table view is paginated, but the user
  // expects this button to chew through *every* processable file the server
  // knows about, not just the ones currently rendered. We fetch each
  // processable status with a max page-size loop and concatenate. Files
  // owned by other PMs are filtered out client-side to match the per-row
  // selector rule (and the backend will skip them anyway).
  const handleProcessAll = useCallback(async () => {
    if (processing) {
      message.info("A batch is already in progress");
      return;
    }
    const statuses = ["pending", "failed", "skipped"];
    setLoading(true);
    try {
      const collected = [];
      const seen = new Set();
      for (const st of statuses) {
        let page = 1;
        // Page size capped at 100 by the backend.
        while (true) {
          const data = await listBuildPlanImports({
            page,
            pageSize: 100,
            status: st,
          });
          const items = data?.items || [];
          for (const r of items) {
            if (seen.has(r.id)) continue;
            seen.add(r.id);
            collected.push(r);
          }
          if (items.length < 100) break;
          page += 1;
          if (page > 100) break; // hard safety cap (10k files)
        }
      }
      const eligible = collected.filter((r) => canActOn(r));
      const ineligible = collected.length - eligible.length;
      if (!eligible.length) {
        message.info(
          ineligible > 0
            ? `No files you uploaded are pending. (${ineligible} owned by other PMs were skipped.)`
            : "No pending files to process.",
        );
        return;
      }
      if (ineligible > 0) {
        message.info(
          `Processing ${eligible.length} file(s). Skipped ${ineligible} owned by other PMs.`,
        );
      }
      await handleProcess(
        eligible.map((r) => r.id),
        { files: eligible },
      );
    } catch (err) {
      message.error(`Could not start batch: ${err.message}`);
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [processing, canActOn]);

  // When a background run finishes, refresh from the server and prune the
  // selection back to anything that still failed so retry is one click.
  //
  // We track the timestamp we've already reacted to in a ref so this effect
  // *only* fires on the leading edge of a real completion. Otherwise, when
  // the user navigates away mid-batch and comes back, the stale timestamp
  // from a *previous* completed batch would re-trigger this handler on
  // mount — wiping selectedIds and clearing the in-flight row overrides for
  // the batch that's currently still running.
  const handledCompletionAtRef = useRef(lastRunCompletedAt);
  useEffect(() => {
    if (!lastRunCompletedAt) return;
    if (lastRunCompletedAt === handledCompletionAtRef.current) return;
    handledCompletionAtRef.current = lastRunCompletedAt;
    let cancelled = false;
    (async () => {
      await loadData();
      if (cancelled) return;
      // After loadData repopulates rows, drop overrides + tighten selection.
      setRows((prev) => {
        setSelectedIds((sel) =>
          sel.filter((id) => {
            const r = prev.find((x) => x.id === id);
            return r && r.status === "failed";
          }),
        );
        return prev;
      });
      clearOverrides();
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastRunCompletedAt]);

  // If the user lands on this page while a batch is already running, mirror
  // the active ids in the checklist so the UI doesn't look idle. We re-sync
  // whenever the set of active ids changes too (e.g. the store narrowed it
  // down to processable ids after the pre-count) so any files that are
  // currently queued/processing stay checked across navigations.
  useEffect(() => {
    if (processing && activeIds.length) {
      setSelectedIds((sel) => {
        const merged = new Set(sel);
        activeIds.forEach((id) => merged.add(id));
        return Array.from(merged);
      });
    }
  }, [processing, activeIds]);

  // Apply in-flight row overrides on top of the server-fetched rows.
  const displayRows = useMemo(() => {
    if (!Object.keys(rowOverrides).length) return rows;
    return rows.map((r) =>
      rowOverrides[r.id] ? { ...r, ...rowOverrides[r.id] } : r,
    );
  }, [rows, rowOverrides]);

  const processableSelected = useMemo(
    () => selectedIds.filter((id) => {
      const row = displayRows.find((r) => r.id === id);
      return row && PROCESSABLE.has(row.status) && canActOn(row);
    }),
    [selectedIds, displayRows, canActOn],
  );

  const columns = useMemo(
    () => [
      {
        title: "File",
        dataIndex: "original_filename",
        key: "original_filename",
        sorter: true,
        sortOrder: sort.column === "original_filename" ? sort.order : null,
        ...textSearchFilter((r) => r.original_filename, "Search filename"),
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
        title: "WW / Year / Rev",
        key: "ww",
        width: 140,
        sorter: true,
        sortOrder: sort.column === "ww" ? sort.order : null,
        render: (_, r) => {
          const ww = r.work_week != null ? `WW${String(r.work_week).padStart(2, "0")}` : "—";
          const yr = r.work_year ?? "—";
          const rev = r.file_revision != null ? `rev${r.file_revision}` : "—";
          return `${ww} / ${yr} / ${rev}`;
        },
      },
      {
        title: "Status",
        dataIndex: "status",
        key: "status",
        width: 160,
        filters: valueFilters(Object.keys(STATUS_COLORS)),
        onFilter: (value, record) => record.status === value,
        sorter: true,
        sortOrder: sort.column === "status" ? sort.order : null,
        render: (s, r) => {
          if (s === "processing") {
            const label =
              progress?.mode === "reprocess" ? "re-processing" : "processing";
            return (
              <Space size={6}>
                <Spin size="small" />
                <Tag color={STATUS_COLORS.processing}>{label}</Tag>
              </Space>
            );
          }
          // While the batch is running and this row is queued (still pending/failed)
          // give a subtle hint that it's waiting in line.
          if (
            progress &&
            progress.currentId !== r.id &&
            (s === "pending" || s === "failed")
          ) {
            return (
              <Space size={6}>
                <Tag color={STATUS_COLORS[s] || "default"}>{s}</Tag>
                <Text type="secondary" style={{ fontSize: 11 }}>queued</Text>
              </Space>
            );
          }
          return <Tag color={STATUS_COLORS[s] || "default"}>{s}</Tag>;
        },
      },
      {
        title: "Uploaded By",
        key: "uploaded_by",
        sorter: true,
        sortOrder: sort.column === "uploaded_by" ? sort.order : null,
        ...textSearchFilter(
          (r) => r.uploaded_by?.full_name || r.uploaded_by?.email,
          "Search uploader",
        ),
        render: (_, r) => r.uploaded_by?.full_name || r.uploaded_by?.email || "—",
      },
      {
        title: "Uploaded At",
        dataIndex: "created_at",
        key: "created_at",
        sorter: true,
        sortOrder: sort.column === "created_at" ? sort.order : null,
        render: formatDate,
      },
      {
        title: "Processed At",
        dataIndex: "processed_at",
        key: "processed_at",
        sorter: true,
        sortOrder: sort.column === "processed_at" ? sort.order : null,
        render: formatDate,
      },
      {
        title: "Actions",
        key: "actions",
        width: 200,
        render: (_, record) => (
          <Space>
            <Tooltip title="View details">
              <Button
                size="small"
                icon={<EyeOutlined />}
                onClick={() => setDetail(record)}
              />
            </Tooltip>
            <Tooltip title="Edit WW / Year / Rev">
              <Button
                size="small"
                icon={<EditOutlined />}
                onClick={() => openEdit(record)}
              />
            </Tooltip>
            <Tooltip title={PROCESSABLE.has(record.status) ? "Process" : "Reprocess"}>
              <Button
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => handleReprocess(record.id)}
                disabled={!canActOn(record)}
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
    [progress, canActOn, sort],
  );

  return (
    <Space orientation="vertical" size="large" style={{ width: "100%" }}>
      <div>
        <Title level={3} style={{ marginBottom: 0 }}>
          Import Build Plan
        </Title>
        <Paragraph type="secondary" style={{ marginTop: 4 }}>
          Drag and drop historical build plan Excel files (.xlsx). Files are
          stored on the server and listed below in <Text code>pending</Text>{" "}
          state. <Text strong>Nothing is written to the database</Text> until
          you select one or more rows and click <Text code>Process</Text>.
          Files with the exact same contents as an earlier upload are detected
          and skipped automatically.
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
            Click or drag build plan files to this area to upload
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
              onClick={() => handleProcess(processableSelected)}
            >
              Process Selected ({processableSelected.length})
            </Button>
            <Popconfirm
              title="Process all pending and failed files?"
              description="This processes every processable file you uploaded, across all pages."
              onConfirm={handleProcessAll}
              disabled={processing}
            >
              <Button
                icon={<ThunderboltOutlined />}
                loading={processing}
                disabled={processing}
              >
                Process All
              </Button>
            </Popconfirm>
            <Button onClick={() => loadData()} icon={<ReloadOutlined />} disabled={processing}>
              Refresh
            </Button>
          </Space>
        }
      >
        <Tabs
          activeKey={scope}
          onChange={(key) => {
            // Switching tabs is conceptually a new query, so reset the
            // selection (which is row-id based and may refer to rows that
            // are no longer in view) and jump back to page 1.
            setScope(key);
            setSelectedIds([]);
            loadData(1, pagination.pageSize, undefined, key);
          }}
          items={[
            { key: "all", label: "All" },
            { key: "mine", label: "Imported By Me" },
          ]}
          style={{ marginBottom: 8 }}
        />
        {progress && (
          <Alert
            type="info"
            showIcon
            style={{ marginBottom: 12 }}
            message={
              <Space orientation="vertical" size={6} style={{ width: "100%" }}>
                <Text strong>
                  {progress.mode === "reprocess" ? "Re-processing" : "Processing"}{" "}
                  build plan {progress.donePlans} / {progress.totalPlans || "?"}
                  {" · "}File {progress.fileIndex} of {progress.files}
                  {progress.currentName ? ` — ${progress.currentName}` : ""}
                </Text>
                <Progress
                  percent={
                    progress.totalPlans > 0
                      ? Math.min(
                          100,
                          Math.round((progress.donePlans / progress.totalPlans) * 100),
                        )
                      : 0
                  }
                  status={
                    progress.failedFiles > 0
                      ? "exception"
                      : progress.donePlans >= progress.totalPlans && progress.totalPlans > 0
                      ? "success"
                      : "active"
                  }
                  size="small"
                />
                {progress.currentTotal > 0 && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Current file: {progress.currentDone} / {progress.currentTotal} build plans
                    {progress.lastConfig ? ` · last: ${progress.lastConfig}` : ""}
                  </Text>
                )}
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Files: {progress.succeededFiles} succeeded · {progress.failedFiles} failed
                  {progress.skippedFiles ? ` · ${progress.skippedFiles} skipped` : ""}
                  {progress.notFoundFiles ? ` · ${progress.notFoundFiles} not found` : ""}
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
            // Only allow expansion for rows that actually have something to
            // show (an error message or a parse summary). This is the easiest
            // way to surface the error log without forcing the user to open
            // the details modal for every failed file.
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
                {r.summary?.warnings?.length > 0 && (
                  <Alert
                    type="warning"
                    showIcon
                    message={`${r.summary.warnings.length} warning(s)`}
                    description={
                      <ul style={{ marginBottom: 0 }}>
                        {r.summary.warnings.map((w, i) => (
                          <li key={i}>{w}</li>
                        ))}
                      </ul>
                    }
                  />
                )}
                {r.summary && (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {r.summary.new_build_plans ?? 0} new ·{" "}
                    {r.summary.revisions_created ?? 0} revision(s) ·{" "}
                    {r.summary.no_change_touches ?? 0} unchanged
                    {(r.summary.revisions_inserted_midstream ?? 0) > 0 && (
                      <> · {r.summary.revisions_inserted_midstream} mid-history</>
                    )}
                    {" · "}
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
            getCheckboxProps: (record) => {
              // Only the uploader (or an admin) may process a file, so
              // void the row's checkbox for everyone else. Tooltip is on
              // the wrapper via `title` so antd surfaces the reason.
              const allowed = canActOn(record);
              return {
                name: record.original_filename,
                disabled: !allowed,
                title: allowed
                  ? undefined
                  : "Only the PM who uploaded this file can process it",
              };
            },
          }}
          pagination={{
            current: pagination.current,
            pageSize: pagination.pageSize,
            total: pagination.total,
            showSizeChanger: true,
          }}
          onChange={handleTableChange}
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
                <Space orientation="vertical" size={4} style={{ width: "100%" }}>                  <Text>
                    <strong>New build plans:</strong>{" "}
                    {detail.summary.new_build_plans ?? 0}
                  </Text>
                  <Text>
                    <strong>Revisions created:</strong>{" "}
                    {detail.summary.revisions_created ?? 0}
                    {(detail.summary.revisions_inserted_midstream ?? 0) > 0 && (
                      <> ({detail.summary.revisions_inserted_midstream} inserted mid-history)</>
                    )}
                  </Text>
                  <Text>
                    <strong>Unchanged (touches):</strong>{" "}
                    {detail.summary.no_change_touches ?? 0}
                  </Text>
                  <Text>
                    <strong>Sheets processed:</strong>{" "}
                    {detail.summary.sheets_processed ?? 0}
                  </Text>
                  <Text>
                    <strong>Sheets skipped:</strong>{" "}
                    {(detail.summary.sheets_skipped || []).join(", ") || "—"}
                  </Text>
                  <Text>
                    <strong>Columns skipped:</strong>{" "}
                    {detail.summary.columns_skipped ?? 0}
                  </Text>
                  {(detail.summary.status_errors || []).length > 0 && (
                    <Alert
                      type="error"
                      message={`${detail.summary.status_errors.length} status regression error(s)`}
                      description={
                        <ul style={{ marginBottom: 0 }}>
                          {detail.summary.status_errors.map((e, i) => (
                            <li key={i}>{e}</li>
                          ))}
                        </ul>
                      }
                    />
                  )}
                  {(detail.summary.unrecorded_users || []).length > 0 && (
                    <Alert
                      type="warning"
                      message={`Created ${detail.summary.unrecorded_users.length} inactive placeholder user(s)`}
                      description={
                        <ul style={{ marginBottom: 0 }}>
                          {detail.summary.unrecorded_users.map((n) => (
                            <li key={n}>{n}</li>
                          ))}
                        </ul>
                      }
                    />
                  )}
                  {(detail.summary.warnings || []).length > 0 && (
                    <Alert
                      type="info"
                      message="Warnings"
                      description={
                        <ul style={{ marginBottom: 0 }}>
                          {detail.summary.warnings.map((w, i) => (
                            <li key={i}>{w}</li>
                          ))}
                        </ul>
                      }
                    />
                  )}
                </Space>
              </Card>
            )}

            <ImportSheetsViewer fileId={detail.id} status={detail.status} />
          </Space>
        )}
      </Modal>

      <Modal
        open={!!editTarget}
        onCancel={() => setEditTarget(null)}
        onOk={handleEditSave}
        okText="Save"
        title={
          editTarget
            ? `Edit metadata — ${editTarget.original_filename}`
            : "Edit metadata"
        }
        destroyOnClose
      >
        <Paragraph type="secondary" style={{ marginTop: 0 }}>
          Set the work-week, year, and file revision manually when the filename
          can't be auto-parsed. Saving will reset a <Text code>skipped</Text>{" "}
          row back to <Text code>pending</Text> so you can process it.
        </Paragraph>
        <Form form={editForm} layout="vertical" preserve={false}>
          <Form.Item
            name="work_week"
            label="Work Week (1–53)"
            rules={[
              { required: true, message: "Required" },
              { type: "number", min: 1, max: 53, message: "1–53" },
            ]}
          >
            <InputNumber min={1} max={53} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            name="work_year"
            label="Year (e.g. 2026)"
            rules={[
              { required: true, message: "Required" },
              { type: "number", min: 2000, max: 2099, message: "2000–2099" },
            ]}
          >
            <InputNumber min={2000} max={2099} style={{ width: "100%" }} />
          </Form.Item>
          <Form.Item
            name="file_revision"
            label="File Revision"
            rules={[
              { required: true, message: "Required" },
              { type: "number", min: 0, message: ">= 0" },
            ]}
          >
            <InputNumber min={0} style={{ width: "100%" }} />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

/* ----------------------------------------------------------------------
 * ImportSheetsViewer
 *
 * Renders the rows we parsed from the auxiliary sheets ("Shipping Info"
 * and "Si") of a single import file. Lazy-loads on mount and tabs between
 * the two sheets. Only rendered when a file is in the success state — for
 * pending / failed files there's nothing to show.
 * -------------------------------------------------------------------- */
function ImportSheetsViewer({ fileId, status }) {
  const [loading, setLoading] = useState(false);
  const [shipping, setShipping] = useState([]);
  const [si, setSi] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!fileId || status !== "success") return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([getImportShippingInfos(fileId), getImportSiRows(fileId)])
      .then(([s, r]) => {
        if (cancelled) return;
        setShipping(s || []);
        setSi(r || []);
      })
      .catch((err) => !cancelled && setError(err.message || String(err)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [fileId, status]);

  if (status !== "success") return null;

  const shippingColumns = [
    { title: "#", dataIndex: "row_index", width: 60, render: (v) => v ?? "—" },
    { title: "Responsibility", dataIndex: "responsibility", render: (v) => v || "—" },
    { title: "Name", dataIndex: "name", render: (v) => v || "—" },
    { title: "Address", dataIndex: "address", render: (v) => v || "—" },
  ];

  const siColumns = [
    { title: "#", dataIndex: "row_index", width: 50, render: (v) => v ?? "—" },
    { title: "Si Description", dataIndex: "si_description", render: (v) => v || "—" },
    { title: "Si Lot Numbers", dataIndex: "si_lot_numbers", render: (v) => v || "—" },
    { title: "Class Test Rev", dataIndex: "class_test_rev", render: (v) => v || "—" },
    { title: "Req Qty", dataIndex: "request_qty", width: 80, render: (v) => v ?? "—" },
    { title: "Req Dock", dataIndex: "request_dock_date", render: (v) => v || "—" },
    { title: "Commit Qty", dataIndex: "commit_qty", width: 90, render: (v) => v ?? "—" },
    { title: "Commit Dock", dataIndex: "commit_dock_date", render: (v) => v || "—" },
    { title: "Actual Qty", dataIndex: "actual_qty", width: 90, render: (v) => v ?? "—" },
    { title: "Actual Dock", dataIndex: "actual_dock_date", render: (v) => v || "—" },
    { title: "Comments", dataIndex: "comments", render: (v) => v || "—" },
  ];

  return (
    <Card size="small" title="Extra sheets">
      {error && <Alert type="error" message={error} style={{ marginBottom: 8 }} />}
      <Spin spinning={loading}>
        <Tabs
          defaultActiveKey="shipping"
          items={[
            {
              key: "shipping",
              label: `Shipping Info (${shipping.length})`,
              children: (
                <Table
                  size="small"
                  rowKey="id"
                  columns={shippingColumns}
                  dataSource={shipping}
                  pagination={shipping.length > 10 ? { pageSize: 10 } : false}
                  locale={{ emptyText: "No Shipping Info rows in this file" }}
                  scroll={{ x: "max-content" }}
                />
              ),
            },
            {
              key: "si",
              label: `Si (${si.length})`,
              children: (
                <Table
                  size="small"
                  rowKey="id"
                  columns={siColumns}
                  dataSource={si}
                  pagination={si.length > 10 ? { pageSize: 10 } : false}
                  locale={{ emptyText: "No Si rows in this file" }}
                  scroll={{ x: "max-content" }}
                />
              ),
            },
          ]}
        />
      </Spin>
    </Card>
  );
}
