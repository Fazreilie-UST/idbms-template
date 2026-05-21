import { useNavigate, useLocation } from "react-router-dom";
import { Card, Input, Segmented, Space, Table, Tag, Typography, Alert } from "antd";
import { SearchOutlined, AppstoreOutlined, UserOutlined } from "@ant-design/icons";
import { useBuildRequestTable } from "@/features/orders/hooks/useBuildRequestTable";

const { Title } = Typography;

const STATUS_COLORS = {
  Draft: "default",
  Submitted: "processing",
  "Under Review": "warning",
  Approved: "success",
  Planned: "blue",
  Locked: "purple",
  Cancelled: "error",
  Rejected: "error",
  Completed: "success",
  None: "default",
};

const STATUSES = [
  "Draft",
  "Submitted",
  "Under Review",
  "Approved",
  "Planned",
  "Locked",
  "Completed",
  "Rejected",
  "Cancelled",
];

export default function BuildRequestManager() {
  const navigate = useNavigate();
  const location = useLocation();
  const isRequestor = location.pathname.startsWith("/requestor");
  const basePath = isRequestor ? "/requestor/build-requests" : "/pm/build-requests";

  const {
    rows,
    loading,
    error,
    pagination,
    filters,
    updateFilters,
    handleTableChange,
  } = useBuildRequestTable(
    isRequestor ? { my_orders: true } : { my_plans: true }
  );

  const columns = [
    {
      title: "ID",
      dataIndex: "id",
      width: 80,
      sorter: (a, b) => a.id - b.id,
      defaultSortOrder: "descend",
    },
    {
      title: "Config Number",
      dataIndex: "config_number",
      render: (v) => v || "\u2014",
    },
    {
      title: "Family / Form Factor",
      key: "fs",
      render: (_, r) =>
        [r.family_code, r.form_factor].filter(Boolean).join(" / ") || "\u2014",
    },
    {
      title: "Quantity",
      dataIndex: "quantity",
      width: 100,
      sorter: (a, b) => a.quantity - b.quantity,
    },
    {
      title: "Revision",
      dataIndex: "revision",
      width: 100,
      render: (v) => `rev${v ?? 1}`,
    },
    {
      title: "Status",
      dataIndex: "status",
      width: 140,
      render: (s) => <Tag color={STATUS_COLORS[s] || "default"}>{s}</Tag>,
    },
    {
      title: "Requestor",
      key: "requestor",
      render: (_, r) => r.requestor?.full_name || r.requestor?.email || `#${r.requestor_id}`,
    },
  ];

  const segmentValue =
    filters.status || (isRequestor ? "all" : "managed");

  const segmentOptions = isRequestor
    ? [
        { label: "All", value: "all", icon: <AppstoreOutlined /> },
        { label: "Mine", value: "mine", icon: <UserOutlined /> },
        ...STATUSES.map((s) => ({ label: s, value: s })),
      ]
    : [
        { label: "Managed by me", value: "managed", icon: <UserOutlined /> },
        ...STATUSES.map((s) => ({ label: s, value: s })),
      ];

  function onSegmentChange(v) {
    if (isRequestor) {
      if (v === "all") {
        updateFilters({ status: "", my_orders: false });
      } else if (v === "mine") {
        updateFilters({ status: "", my_orders: true });
      } else {
        updateFilters({ status: v });
      }
    } else {
      // PM view is always scoped to plans the user manages.
      if (v === "managed") {
        updateFilters({ status: "", my_plans: true });
      } else {
        updateFilters({ status: v, my_plans: true });
      }
    }
  }

  return (
    <Card>
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
        <Title level={3} style={{ margin: 0 }}>
          {isRequestor ? "My Build Requests" : "Manage Build Requests"}
        </Title>
        <Space>
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder="Search config number\u2026"
            value={filters.search}
            onChange={(e) => updateFilters({ search: e.target.value })}
            style={{ width: 260 }}
          />
        </Space>
      </div>

      <Segmented
        options={segmentOptions}
        value={segmentValue}
        onChange={onSegmentChange}
        style={{ marginBottom: 16 }}
      />

      {error && (
        <Alert
          type="error"
          message="Failed to load build requests"
          description={error}
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

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
          onClick: () => navigate(`${basePath}/${record.id}`),
          style: { cursor: "pointer" },
        })}
      />
    </Card>
  );
}
