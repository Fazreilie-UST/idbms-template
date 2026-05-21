import { Card, Input, Segmented, Space, Table, Tag, Typography, Alert } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import { useShippingTable } from "@/features/shipments/hooks/useShippingTable";

const { Title } = Typography;

const STATUS_COLORS = {
  Scheduled: "processing",
  ShippedOut: "warning",
  Delivered: "success",
  Completed: "success",
};

const STATUSES = ["All", "Scheduled", "ShippedOut", "Delivered", "Completed"];

export default function ShippingTracker() {
  const {
    rows,
    loading,
    error,
    pagination,
    filters,
    sort,
    updateFilters,
    handleTableChange,
  } = useShippingTable();

  function sortedFor(field) {
    if (sort?.sort_by !== field) return null;
    return sort.sort_order === "asc" ? "ascend" : "descend";
  }

  const columns = [
    {
      title: "ID",
      dataIndex: "id",
      key: "id",
      width: 80,
      sorter: true,
      sortOrder: sortedFor("id"),
      defaultSortOrder: "descend",
    },
    {
      title: "Config Number",
      dataIndex: "config_number",
      key: "config_number",
      sorter: true,
      sortOrder: sortedFor("config_number"),
      render: (v) => v || "\u2014",
    },
    {
      title: "Tracking #",
      dataIndex: "tracking_number",
      key: "tracking_number",
      sorter: true,
      sortOrder: sortedFor("tracking_number"),
      render: (v) => v || "\u2014",
    },
    {
      title: "Forwarder",
      dataIndex: "forwarder",
      key: "forwarder",
      sorter: true,
      sortOrder: sortedFor("forwarder"),
      render: (v) => v || "\u2014",
    },
    {
      title: "Quantity",
      dataIndex: "quantity",
      key: "quantity",
      width: 110,
      sorter: true,
      sortOrder: sortedFor("quantity"),
    },
    {
      title: "Ship Date",
      dataIndex: "ship_date",
      key: "ship_date",
      sorter: true,
      sortOrder: sortedFor("ship_date"),
      render: (v) => v || "\u2014",
    },
    {
      title: "ETA",
      dataIndex: "eta",
      key: "eta",
      sorter: true,
      sortOrder: sortedFor("eta"),
      render: (v) => v || "\u2014",
    },
    {
      title: "Delivery Date",
      dataIndex: "delivery_date",
      key: "delivery_date",
      sorter: true,
      sortOrder: sortedFor("delivery_date"),
      render: (v) => v || "\u2014",
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 130,
      sorter: true,
      sortOrder: sortedFor("status"),
      render: (s) => <Tag color={STATUS_COLORS[s] || "default"}>{s}</Tag>,
    },
    {
      title: "Handler",
      key: "recipient_user",
      sorter: true,
      sortOrder: sortedFor("recipient_user"),
      render: (_, r) => r.recipient_user?.full_name || "\u2014",
    },
    {
      title: "Recipients",
      key: "recipients",
      render: (_, r) => {
        const list = r.recipients || [];
        if (!list.length) return "\u2014";
        return list.map((u) => u.full_name).filter(Boolean).join(", ");
      },
    },
  ];

  return (
    <Card>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, gap: 12, flexWrap: "wrap" }}>
        <Title level={3} style={{ margin: 0 }}>Shipment Tracker</Title>
        <Space>
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder="Search (config #, tracking, handler\u2026)"
            value={filters.search}
            onChange={(e) => updateFilters({ search: e.target.value })}
            style={{ width: 280 }}
          />
        </Space>
      </div>

      <Segmented
        options={STATUSES}
        value={filters.status || "All"}
        onChange={(v) => updateFilters({ status: v === "All" ? "" : v })}
        style={{ marginBottom: 16 }}
      />

      {error && <Alert type="error" message="Failed to load" description={error} showIcon style={{ marginBottom: 16 }} />}

      <Table
        rowKey="id"
        columns={columns}
        dataSource={rows}
        loading={loading}
        pagination={{
          current: pagination.page,
          pageSize: pagination.page_size,
          total: pagination.total,
          showSizeChanger: true,
          showTotal: (t) => `Total ${t} records`,
        }}
        onChange={handleTableChange}
      />
    </Card>
  );
}
