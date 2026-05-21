import { useEffect, useState } from "react";
import { Card, Input, Space, Table, Tag, Typography, Alert, Select } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import { useBuildRequestTable } from "@/features/orders/hooks/useBuildRequestTable";
import { fetchBuildRequestFilterOptions } from "@/features/orders/services/build_request_filter_options";

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
};

export default function BuildRequestTracker() {
  const {
    rows,
    loading,
    error,
    pagination,
    filters,
    sort,
    updateFilters,
    handleTableChange,
  } = useBuildRequestTable();

  const [options, setOptions] = useState({
    families: [],
    form_factors: [],
    requestors: [],
    statuses: [],
  });

  useEffect(() => {
    fetchBuildRequestFilterOptions()
      .then((d) => setOptions(d || {}))
      .catch(() => {});
  }, []);

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
      title: "Family",
      dataIndex: "family_code",
      key: "family",
      sorter: true,
      sortOrder: sortedFor("family"),
      render: (v) => v || "\u2014",
    },
    {
      title: "Form Factor",
      dataIndex: "form_factor",
      key: "form_factor",
      sorter: true,
      sortOrder: sortedFor("form_factor"),
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
      title: "Revision",
      dataIndex: "revision",
      key: "revision",
      width: 110,
      sorter: true,
      sortOrder: sortedFor("revision"),
      render: (v) => `rev${v ?? 1}`,
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 160,
      sorter: true,
      sortOrder: sortedFor("status"),
      render: (s) => <Tag color={STATUS_COLORS[s] || "default"}>{s}</Tag>,
    },
    {
      title: "Requestor",
      key: "requestor",
      sorter: true,
      sortOrder: sortedFor("requestor"),
      render: (_, r) =>
        r.requestor?.full_name || r.requestor?.email || `#${r.requestor_id}`,
    },
  ];

  const toCsv = (arr) => (Array.isArray(arr) && arr.length ? arr.join(",") : "");
  const fromCsv = (s) => (s ? String(s).split(",").filter(Boolean) : []);

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
          Build Request Tracker
        </Title>
        <Space wrap>
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder="Search (config #, family, requestor\u2026)"
            value={filters.search}
            onChange={(e) => updateFilters({ search: e.target.value })}
            style={{ width: 280 }}
          />
        </Space>
      </div>

      <Space wrap style={{ marginBottom: 16 }}>
        <Select
          mode="multiple"
          allowClear
          placeholder="Status"
          style={{ minWidth: 200 }}
          value={fromCsv(filters.status)}
          onChange={(v) => updateFilters({ status: toCsv(v) })}
          options={(options.statuses || []).map((s) => ({ value: s, label: s }))}
        />
        <Select
          mode="multiple"
          allowClear
          placeholder="Family"
          style={{ minWidth: 200 }}
          value={fromCsv(filters.family)}
          onChange={(v) => updateFilters({ family: toCsv(v) })}
          options={(options.families || []).map((s) => ({ value: s, label: s }))}
        />
        <Select
          mode="multiple"
          allowClear
          placeholder="Form Factor"
          style={{ minWidth: 200 }}
          value={fromCsv(filters.form_factor)}
          onChange={(v) => updateFilters({ form_factor: toCsv(v) })}
          options={(options.form_factors || []).map((s) => ({
            value: s,
            label: s,
          }))}
        />
        <Select
          mode="multiple"
          allowClear
          placeholder="Requestor"
          style={{ minWidth: 240 }}
          value={fromCsv(filters.requestor).map((x) =>
            Number.isNaN(Number(x)) ? x : Number(x),
          )}
          onChange={(v) => updateFilters({ requestor: toCsv(v) })}
          options={(options.requestors || []).map((u) => ({
            value: u.id,
            label: u.label || u.full_name || u.email || `#${u.id}`,
          }))}
          filterOption={(input, option) =>
            (option?.label || "").toLowerCase().includes(input.toLowerCase())
          }
        />
      </Space>

      {error && (
        <Alert
          type="error"
          message="Failed to load"
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
          showTotal: (t) => `Total ${t} records`,
        }}
        onChange={handleTableChange}
      />
    </Card>
  );
}
