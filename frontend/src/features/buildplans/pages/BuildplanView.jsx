import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Breadcrumb,
  Button,
  Card,
  Col,
  Descriptions,
  Modal,
  Row,
  Space,
  Spin,
  Table,
  Tabs,
  Tag,
  Typography,
  Alert,
  message,
} from "antd";
import { ArrowLeftOutlined, FileSearchOutlined, UsergroupAddOutlined } from "@ant-design/icons";
import { fetchBuildPlanById, fetchBuildPlanExtraSheets } from "@/features/buildplans/services/build_plan_service";
import {
  fetchBuildPlanRevisions,
  createBuildPlanRevision,
} from "@/features/buildplans/services/build_plan_revision_service";
import RevisionCarousel from "@/features/buildplans/components/RevisionCarousel";
import AddRevisionModal from "@/features/buildplans/components/AddRevisionModal";
import GrantAccessModal from "@/features/buildplans/components/GrantAccessModal";

const { Title } = Typography;

function renderValue(value) {
  if (value === null || value === undefined || value === "") return "-";
  return value;
}

function renderBuildNotes(value) {
  let notes = [];
  if (Array.isArray(value)) {
    notes = value;
  } else if (typeof value === "string") {
    notes = value
      .replace(/^{|}$/g, "")
      .split(",")
      .map((n) => n.trim())
      .filter(Boolean);
  }
  if (!notes.length) return "-";
  return (
    <Space wrap size={[4, 4]}>
      {notes.map((note) => (
        <Tag key={note}>{note}</Tag>
      ))}
    </Space>
  );
}

/**
 * Inject silicon_steppings (stored in a separate table on the backend) as
 * a "Stepping" attribute on the "Silicon" component row, so the UI presents
 * it as part of the Silicon key-component attributes. If no Silicon row
 * exists yet, one is synthesized with just the Stepping attribute.
 */
function mergeSiliconStepping(components, steppings) {
  const list = Array.isArray(components) ? [...components] : [];
  const items = Array.isArray(steppings) ? steppings.filter(Boolean) : [];
  if (!items.length) return list;

  const steppingValue = items.join(", ");
  const idx = list.findIndex(
    (c) => (c?.component_name || "").toLowerCase() === "silicon"
  );
  if (idx === -1) {
    list.unshift({
      component_name: "Silicon",
      component_slot: null,
      supplier: null,
      attributes: [{ name: "Stepping", value: steppingValue }],
    });
    return list;
  }
  const existing = list[idx];
  const attrs = Array.isArray(existing.attributes) ? [...existing.attributes] : [];
  const hasStepping = attrs.some(
    (a) => (a?.name || "").toLowerCase() === "stepping"
  );
  if (!hasStepping) {
    attrs.unshift({ name: "Stepping", value: steppingValue });
  }
  list[idx] = { ...existing, attributes: attrs };
  return list;
}

const componentColumns = [
  {
    title: "Component",
    dataIndex: "component_name",
    key: "component_name",
    sorter: (a, b) => (a.component_name || "").localeCompare(b.component_name || ""),
  },
  {
    title: "Slot",
    dataIndex: "component_slot",
    key: "component_slot",
  },
  {
    title: "Supplier",
    dataIndex: "supplier",
    key: "supplier",
  },
  {
    title: "Attributes",
    key: "attributes",
    render: (_, row) => (
      <Space wrap>
        {(row.attributes || []).map((attr) => (
          <Tag key={`${attr.name}-${attr.value}`}>
            {attr.name}: {attr.value}
          </Tag>
        ))}
      </Space>
    ),
  },
];

const testColumns = [
  {
    title: "Test",
    dataIndex: "test_name",
    key: "test_name",
  },
  {
    title: "Detail",
    dataIndex: "test_detail",
    key: "test_detail",
  },
];

const orderColumns = [
  {
    title: "Order ID",
    dataIndex: "build_request_id",
    key: "build_request_id",
    sorter: (a, b) => a.build_request_id - b.build_request_id,
  },
  {
    title: "Requestor",
    dataIndex: "requestor_name",
    key: "requestor_name",
    sorter: (a, b) => (a.requestor_name || "").localeCompare(b.requestor_name || ""),
  },
  {
    title: "Quantity",
    dataIndex: "quantity",
    key: "quantity",
    sorter: (a, b) => a.quantity - b.quantity,
  },
];

const warehouseColumns = [
  {
    title: "Warehouse",
    dataIndex: "warehouse_name",
    key: "warehouse_name",
  },
  {
    title: "Quantity Stored",
    dataIndex: "quantity_stored",
    key: "quantity_stored",
    sorter: (a, b) => (a.quantity_stored || 0) - (b.quantity_stored || 0),
  },
];

const shipmentColumns = [
  {
    title: "Shipment ID",
    dataIndex: "shipment_id",
    key: "shipment_id",
    sorter: (a, b) => a.shipment_id - b.shipment_id,
  },
  {
    title: "Tracking",
    dataIndex: "tracking_number",
    key: "tracking_number",
    render: (value) => value || "-",
  },
  {
    title: "Forwarder",
    dataIndex: "forwarder",
    key: "forwarder",
    render: (value) => value || "-",
  },
  {
    title: "Quantity",
    dataIndex: "quantity",
    key: "quantity",
    sorter: (a, b) => (a.quantity || 0) - (b.quantity || 0),
  },
  {
    title: "Ship Date",
    dataIndex: "ship_date",
    key: "ship_date",
    sorter: (a, b) => (a.ship_date || "").localeCompare(b.ship_date || ""),
    render: (value) => value || "-",
  },
  {
    title: "ETA",
    dataIndex: "eta",
    key: "eta",
    render: (value) => value || "-",
  },
  {
    title: "Delivery Date",
    dataIndex: "delivery_date",
    key: "delivery_date",
    render: (value) => value || "-",
  },
  {
    title: "Handler",
    key: "handler",
    render: (_, row) => row.recipient_user?.full_name || "-",
  },
  {
    title: "Recipients",
    key: "recipients",
    render: (_, row) => {
      const list = row.recipients || [];
      if (list.length === 0) return "-";
      return (
        <div style={{ display: "flex", flexDirection: "column" }}>
          {list.map((r, i) => (
            <span key={`recip-${r.user_id ?? "none"}-${i}`}>
              {r.name || "-"}
              {r.quantity != null ? ` (qty: ${r.quantity})` : ""}
            </span>
          ))}
        </div>
      );
    },
  },
  {
    title: "Comments",
    dataIndex: "comments",
    key: "comments",
    render: (value) => value || "-",
  },
];

export default function BuildplanView() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [data, setData] = useState(null);
  const [revisions, setRevisions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [addOpen, setAddOpen] = useState(false);
  const [grantOpen, setGrantOpen] = useState(false);
  const [submittingRevision, setSubmittingRevision] = useState(false);
  const [extraOpen, setExtraOpen] = useState(false);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const [result, revs] = await Promise.all([
        fetchBuildPlanById(id),
        fetchBuildPlanRevisions(id).catch(() => ({ revisions: [] })),
      ]);
      setData(result);
      setRevisions(revs?.revisions || []);
    } catch (err) {
      setError(err.message || "Failed to load build plan.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function handleCreateRevision(payload) {
    setSubmittingRevision(true);
    try {
      await createBuildPlanRevision(id, payload);
      message.success("New revision created.");
      setAddOpen(false);
      await reload();
    } catch (err) {
      message.error(err.message || "Failed to create revision.");
    } finally {
      setSubmittingRevision(false);
    }
  }

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "80px 0" }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        type="error"
        message="Failed to load build plan"
        description={error}
        showIcon
        action={
          <Button size="small" onClick={() => navigate(-1)}>
            Go Back
          </Button>
        }
      />
    );
  }

  return (
    <>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
            Back
          </Button>
          <Breadcrumb
            items={[
              { title: "Build Plans", onClick: () => navigate(-1), className: "breadcrumb-link" },
              { title: data?.config_number || `Build Plan #${id}` },
            ]}
          />
        </Space>

        <Button
          type="primary"
          icon={<UsergroupAddOutlined />}
          onClick={() => setGrantOpen(true)}
        >
          Access
        </Button>
      </div>

      <Title level={4} style={{ marginBottom: 24 }}>
        {data?.config_number || `Build Plan #${id}`}
        <Tag style={{ marginLeft: 12, verticalAlign: "middle" }}>{data?.status || "-"}</Tag>
      </Title>

      {/* General Info */}
      <Card style={{ marginBottom: 24 }}>
        <Row gutter={[24, 0]}>
          <Col span={24}>
            <Descriptions
              bordered
              size="small"
              column={{ xs: 1, sm: 2, md: 3 }}
            >
              <Descriptions.Item label="Build Plan ID">{renderValue(data?.build_plan_id)}</Descriptions.Item>
              <Descriptions.Item label="Config Number">{renderValue(data?.config_number)}</Descriptions.Item>
              <Descriptions.Item label="Status">
                {data?.status ? <Tag>{data.status}</Tag> : "-"}
              </Descriptions.Item>
              <Descriptions.Item label="Support Activity">{renderValue(data?.support_activity)}</Descriptions.Item>
              <Descriptions.Item label="Build Description">{renderValue(data?.build_description)}</Descriptions.Item>
              <Descriptions.Item label="Build Notes">{renderBuildNotes(data?.build_notes)}</Descriptions.Item>
              <Descriptions.Item label="Family">{renderValue(data?.family_code)}</Descriptions.Item>
              <Descriptions.Item label="Form Factor">{renderValue(data?.form_factor)}</Descriptions.Item>
              <Descriptions.Item label="Product Code">{renderValue(data?.product_code)}</Descriptions.Item>
              <Descriptions.Item label="MM Number">{renderValue(data?.mm_number)}</Descriptions.Item>
              <Descriptions.Item label="TA Number">{renderValue(data?.ta_number)}</Descriptions.Item>
              <Descriptions.Item label="PBA Number">{renderValue(data?.pba_number)}</Descriptions.Item>
              <Descriptions.Item label="AS Number">{renderValue(data?.as_number)}</Descriptions.Item>
              <Descriptions.Item label="Revision">{renderValue(data?.revision)}</Descriptions.Item>
              <Descriptions.Item label="Build Start Date">{renderValue(data?.build_start_date)}</Descriptions.Item>
              <Descriptions.Item label="Ship Date">{renderValue(data?.ship_date)}</Descriptions.Item>
              <Descriptions.Item label="Required Qty">{renderValue(data?.required_quantity)}</Descriptions.Item>
              <Descriptions.Item label="Estimated Yield">{renderValue(data?.estimated_yield)}</Descriptions.Item>
              <Descriptions.Item label="Year">{renderValue(data?.year)}</Descriptions.Item>
            </Descriptions>
          </Col>
        </Row>
      </Card>

      {/* Tabs for nested data */}
      <Card>
        <Tabs
          defaultActiveKey="components"
          items={[
            {
              key: "components",
              label: `Key Components (${(data?.components || []).length})`,
              children: (
                <Table
                  rowKey={(row) =>
                    `${row.component_name}-${row.component_slot}-${row.supplier || ""}`
                  }
                  size="small"
                  columns={componentColumns}
                  dataSource={mergeSiliconStepping(
                    data?.components,
                    data?.silicon_steppings
                  )}
                  pagination={false}
                />
              ),
            },
            {
              key: "tests",
              label: `Tests (${(data?.tests || []).length})`,
              children: (
                <Table
                  rowKey={(row) => `${row.test_name}-${row.test_detail || ""}`}
                  size="small"
                  columns={testColumns}
                  dataSource={data?.tests || []}
                  pagination={false}
                />
              ),
            },
            {
              key: "orders",
              label: `Build Requests (${(data?.build_requests || []).length})`,
              children: (
                <Table
                  rowKey="build_request_id"
                  size="small"
                  columns={orderColumns}
                  dataSource={data?.build_requests || []}
                  pagination={false}
                  summary={(rows) => {
                    const total = rows.reduce(
                      (acc, r) => acc + (Number(r.quantity) || 0),
                      0
                    );
                    return (
                      <Table.Summary fixed>
                        <Table.Summary.Row>
                          <Table.Summary.Cell index={0} colSpan={2}>
                            <strong>Total</strong>
                          </Table.Summary.Cell>
                          <Table.Summary.Cell index={2}>
                            <strong>{total}</strong>
                          </Table.Summary.Cell>
                        </Table.Summary.Row>
                      </Table.Summary>
                    );
                  }}
                />
              ),
            },
            {
              key: "warehouses",
              label: `Warehouse Quantities (${(data?.warehouses || []).length})`,
              children: (
                <Table
                  rowKey="warehouse_id"
                  size="small"
                  columns={warehouseColumns}
                  dataSource={data?.warehouses || []}
                  pagination={false}
                />
              ),
            },
            {
              key: "shipments",
              label: `Shipments (${(data?.shipments || []).length})`,
              children: (
                <>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "flex-end",
                      marginBottom: 8,
                    }}
                  >
                    <Button
                      icon={<FileSearchOutlined />}
                      onClick={() => setExtraOpen(true)}
                    >
                      View Shipping Info & Si
                    </Button>
                  </div>
                  <Table
                    rowKey="shipment_id"
                    size="small"
                    columns={shipmentColumns}
                    dataSource={data?.shipments || []}
                    pagination={false}
                    scroll={{ x: "max-content" }}
                    summary={(rows) => {
                      const total = rows.reduce(
                        (acc, r) => acc + (Number(r.quantity) || 0),
                        0
                      );
                      const qtyColIdx = shipmentColumns.findIndex(
                        (c) => c.key === "quantity"
                      );
                      return (
                        <Table.Summary fixed>
                          <Table.Summary.Row>
                            <Table.Summary.Cell index={0} colSpan={qtyColIdx}>
                              <strong>Total</strong>
                            </Table.Summary.Cell>
                            <Table.Summary.Cell index={qtyColIdx}>
                              <strong>{total}</strong>
                            </Table.Summary.Cell>
                            <Table.Summary.Cell
                              index={qtyColIdx + 1}
                              colSpan={shipmentColumns.length - qtyColIdx - 1}
                            />
                          </Table.Summary.Row>
                        </Table.Summary>
                      );
                    }}
                  />
                </>
              ),
            },
          ]}
        />
      </Card>

      {/* Revision history (horizontal carousel + add-revision card) */}
      <RevisionCarousel
        revisions={revisions}
        currentStatus={data?.status}
        buildPlanId={data?.build_plan_id}
        onAddRevisionClick={() => setAddOpen(true)}
      />

      <AddRevisionModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onSubmit={handleCreateRevision}
        submitting={submittingRevision}
        latestRevision={
          revisions.length
            ? [...revisions].sort(
                (a, b) =>
                  (a.revision_number ?? 0) - (b.revision_number ?? 0)
              )[revisions.length - 1]
            : null
        }
      />

      <GrantAccessModal
        open={grantOpen}
        onClose={() => setGrantOpen(false)}
        buildPlanIds={data?.build_plan_id ? [data.build_plan_id] : []}
        onGranted={(result) => {
          const parts = [];
          if (result.granted) parts.push(`${result.granted} granted`);
          if (result.upgraded) parts.push(`${result.upgraded} upgraded`);
          if (result.unchanged) parts.push(`${result.unchanged} unchanged`);
          message.success(
            `Access updated${parts.length ? `: ${parts.join(", ")}` : ""}.`,
          );
        }}
      />

      <ExtraSheetsModal
        open={extraOpen}
        buildPlanId={data?.build_plan_id || Number(id)}
        familyCode={data?.family_code}
        formFactor={data?.form_factor}
        onClose={() => setExtraOpen(false)}
      />
    </>
  );
}

/* ----------------------------------------------------------------------
 * ExtraSheetsModal
 *
 * Shows Shipping Info + Si rows aggregated across every import file that
 * touched a build plan in the same family + form factor as the current plan.
 * -------------------------------------------------------------------- */
function ExtraSheetsModal({ open, buildPlanId, familyCode, formFactor, onClose }) {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open || !buildPlanId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);
    fetchBuildPlanExtraSheets(buildPlanId)
      .then((result) => !cancelled && setData(result))
      .catch((err) => !cancelled && setError(err.message || String(err)))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [open, buildPlanId]);

  const files = data?.files || [];
  const filesById = files.reduce((acc, f) => {
    acc[f.id] = f;
    return acc;
  }, {});

  const fileLabel = (fileId) => {
    const f = filesById[fileId];
    if (!f) return `File #${fileId}`;
    const ww =
      f.work_year && f.work_week
        ? `WW${String(f.work_week).padStart(2, "0")}'${String(f.work_year).slice(-2)}`
        : null;
    const rev = f.file_revision != null ? `rev${f.file_revision}` : null;
    const parts = [f.original_filename];
    const meta = [ww, rev].filter(Boolean).join(" · ");
    return meta ? `${parts[0]} (${meta})` : parts[0];
  };

  const shippingColumns = [
    {
      title: "Source File",
      dataIndex: "import_file_id",
      width: 280,
      render: (v) => <Tag>{fileLabel(v)}</Tag>,
    },
    { title: "Responsibility", dataIndex: "responsibility", render: (v) => v || "—" },
    { title: "Name", dataIndex: "name", render: (v) => v || "—" },
    { title: "Address", dataIndex: "address", render: (v) => v || "—" },
  ];

  const siColumns = [
    {
      title: "Source File",
      dataIndex: "import_file_id",
      width: 260,
      render: (v) => <Tag>{fileLabel(v)}</Tag>,
    },
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

  const shipping = data?.shipping_infos || [];
  const si = data?.si_rows || [];

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={1100}
      title={
        <Space size="small" wrap>
          <span>Shipping Info & Si</span>
          {(familyCode || data?.family_code) && (
            <Tag color="blue">Family: {familyCode || data?.family_code}</Tag>
          )}
          {(formFactor || data?.form_factor) && (
            <Tag color="geekblue">Form Factor: {formFactor || data?.form_factor}</Tag>
          )}
        </Space>
      }
      destroyOnClose
    >
      {error && (
        <Alert
          type="error"
          message="Failed to load"
          description={error}
          showIcon
          style={{ marginBottom: 12 }}
        />
      )}
      <Spin spinning={loading}>
        {!loading && files.length === 0 && !error ? (
          <Alert
            type="info"
            showIcon
            message="No import files have produced data for this family + form factor yet."
          />
        ) : (
          <>
            <div style={{ marginBottom: 8, color: "rgba(0,0,0,0.55)" }}>
              Aggregated from {files.length} import file{files.length === 1 ? "" : "s"}.
            </div>
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
                      scroll={{ x: "max-content" }}
                      locale={{ emptyText: "No Shipping Info rows found" }}
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
                      scroll={{ x: "max-content" }}
                      locale={{ emptyText: "No Si rows found" }}
                    />
                  ),
                },
              ]}
            />
          </>
        )}
      </Spin>
    </Modal>
  );
}
