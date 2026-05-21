import { useNavigate } from "react-router-dom";
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

export default function ShippingManager() {
  const navigate = useNavigate();
  const {
    rows,
    loading,
    error,
    pagination,
    filters,
    updateFilters,
    handleTableChange,
  } = useShippingTable();

  const columns = [
    { title: "ID", dataIndex: "id", width: 80, sorter: (a, b) => a.id - b.id, defaultSortOrder: "descend" },
    { title: "Config Number", dataIndex: "config_number", render: (v) => v || "\u2014" },
    { title: "Tracking #", dataIndex: "tracking_number", render: (v) => v || "\u2014" },
    { title: "Forwarder", dataIndex: "forwarder", render: (v) => v || "\u2014" },
    { title: "Quantity", dataIndex: "quantity", width: 100 },
    { title: "Ship Date", dataIndex: "ship_date", render: (v) => v || "\u2014" },
    { title: "ETA", dataIndex: "eta", render: (v) => v || "\u2014" },
    { title: "Delivery Date", dataIndex: "delivery_date", render: (v) => v || "\u2014" },
    {
      title: "Status",
      dataIndex: "status",
      width: 120,
      render: (s) => <Tag color={STATUS_COLORS[s] || "default"}>{s}</Tag>,
    },
    {
      title: "Handler",
      key: "recipient",
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
        <Title level={3} style={{ margin: 0 }}>Shipments</Title>
        <Space>
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder="Search config / tracking\u2026"
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
        }}
        onChange={handleTableChange}
        onRow={(record) => ({
          onClick: () => navigate(`/pm/shippings/${record.id}`),
          style: { cursor: "pointer" },
        })}
      />
    </Card>
  );
}
