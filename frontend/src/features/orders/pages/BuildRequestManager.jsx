import { useEffect, useMemo, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  Alert,
  Button,
  Card,
  Input,
  Segmented,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import {
  ReloadOutlined,
  SearchOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { useBuildRequestTable } from "@/features/orders/hooks/useBuildRequestTable";
import { fetchBuildRequestFilterOptions } from "@/features/orders/services/build_request_filter_options";
import { getServerColumnProps } from "@/shared/components/serverColumnFilter";
import { sortOrderFor } from "@/shared/hooks/usePaginatedTable";

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

const toCsv = (arr) => (Array.isArray(arr) && arr.length ? arr.join(",") : "");
const fromCsv = (s) => (s ? String(s).split(",").filter(Boolean) : []);

export default function BuildRequestManager() {
  const navigate = useNavigate();
  const location = useLocation();
  const isRequestor = location.pathname.startsWith("/requestor");
  const basePath = isRequestor
    ? "/requestor/build-requests"
    : "/pm/build-requests";

  const {
    rows,
    loading,
    error,
    pagination,
    filters,
    sorts,
    updateFilters,
    resetAllFilters,
    handleTableChange,
    loadData,
  } = useBuildRequestTable(
    isRequestor ? { my_orders: true } : { my_plans: true }
  );

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

  // Buffered top-toolbar inputs — only push to server when "Apply" clicked
  const [searchInput, setSearchInput] = useState(filters.search || "");
  const [familyInput, setFamilyInput] = useState(fromCsv(filters.family));
  const [formFactorInput, setFormFactorInput] = useState(
    fromCsv(filters.form_factor)
  );
  const [requestorInput, setRequestorInput] = useState(
    fromCsv(filters.requestor)
  );
  const [statusInput, setStatusInput] = useState(fromCsv(filters.status));

  function applyTopFilters(overrides = {}) {
    const patch = {
      search: searchInput,
      family: toCsv(familyInput),
      form_factor: toCsv(formFactorInput),
      requestor: toCsv(requestorInput),
      ...overrides,
    };
    if (showStatusColumn) {
      patch.status = toCsv(statusInput);
    }
    updateFilters(patch);
  }

  function handleReset() {
    setSearchInput("");
    setFamilyInput([]);
    setFormFactorInput([]);
    setRequestorInput([]);
    setStatusInput([]);
    if (isRequestor) {
      setActiveView("all");
    } else {
      setActiveView("managed");
    }
    resetAllFilters();
  }

  // Status column is only shown for the catch-all view ("Managed by me",
  // "All", or "Mine") because the per-status segments already partition
  // the list.
  const showStatusColumn = !filters.status;

  const requestorOptions = useMemo(
    () =>
      (options.requestors || []).map((u) => ({
        label: u.label || u.full_name || u.email || `#${u.id}`,
        value: String(u.id),
      })),
    [options.requestors]
  );

  const allColumns = [
    {
      title: "ID",
      dataIndex: "id",
      key: "id",
      width: 80,
      sorter: { multiple: 1 },
      sortOrder: sortOrderFor(sorts, "id"),
    },
    {
      title: "Config Number",
      dataIndex: "config_number",
      key: "config_number",
      sortOrder: sortOrderFor(sorts, "config_number"),
      ...getServerColumnProps({
        dataIndex: "config_number",
        title: "Config Number",
        updateFilters,
        filters,
        filterOptions: [],
        sortable: { multiple: 2 },
      }),
      render: (v) => v || "\u2014",
    },
    {
      title: "Family",
      dataIndex: "family_code",
      key: "family",
      sortOrder: sortOrderFor(sorts, "family"),
      ...getServerColumnProps({
        dataIndex: "family_code",
        filterKey: "family",
        title: "Family",
        updateFilters,
        filters,
        filterOptions: options.families || [],
        sortable: { multiple: 3 },
      }),
      render: (v) => v || "\u2014",
    },
    {
      title: "Form Factor",
      dataIndex: "form_factor",
      key: "form_factor",
      sortOrder: sortOrderFor(sorts, "form_factor"),
      ...getServerColumnProps({
        dataIndex: "form_factor",
        title: "Form Factor",
        updateFilters,
        filters,
        filterOptions: options.form_factors || [],
        sortable: { multiple: 4 },
      }),
      render: (v) => v || "\u2014",
    },
    {
      title: "Quantity",
      dataIndex: "quantity",
      key: "quantity",
      width: 100,
      sorter: { multiple: 5 },
      sortOrder: sortOrderFor(sorts, "quantity"),
    },
    {
      title: "Revision",
      dataIndex: "revision",
      key: "revision",
      width: 100,
      sorter: { multiple: 6 },
      sortOrder: sortOrderFor(sorts, "revision"),
      render: (v) => `rev${v ?? 1}`,
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 140,
      sortOrder: sortOrderFor(sorts, "status"),
      ...getServerColumnProps({
        dataIndex: "status",
        title: "Status",
        updateFilters,
        filters,
        filterOptions: options.statuses || STATUSES,
        sortable: { multiple: 7 },
      }),
      render: (s) => <Tag color={STATUS_COLORS[s] || "default"}>{s}</Tag>,
    },
    {
      title: "Requestor",
      key: "requestor",
      sortOrder: sortOrderFor(sorts, "requestor"),
      ...getServerColumnProps({
        dataIndex: "requestor",
        title: "Requestor",
        updateFilters,
        filters,
        filterOptions: requestorOptions,
        sortable: { multiple: 8 },
      }),
      render: (_, r) =>
        r.requestor?.full_name || r.requestor?.email || `#${r.requestor_id}`,
    },
  ];

  const columns = allColumns.filter(
    (c) => showStatusColumn || c.key !== "status"
  );

  const segmentValue =
    filters.status || (isRequestor ? "all" : "managed");
  const [activeView, setActiveView] = useState(segmentValue);

  useEffect(() => {
    setActiveView(filters.status || (isRequestor ? "all" : "managed"));
  }, [filters.status, isRequestor]);

  const segmentOptions = isRequestor
    ? [
        { label: "All", value: "all" },
        { label: "Mine", value: "mine", icon: <UserOutlined /> },
        ...STATUSES.map((s) => ({ label: s, value: s })),
      ]
    : [
        { label: "Managed by me", value: "managed", icon: <UserOutlined /> },
        ...STATUSES.map((s) => ({ label: s, value: s })),
      ];

  function onSegmentChange(v) {
    setActiveView(v);
    setStatusInput([]); // segmented selects override status multi-filter
    if (isRequestor) {
      if (v === "all") {
        updateFilters({ status: "", my_orders: false });
      } else if (v === "mine") {
        updateFilters({ status: "", my_orders: true });
      } else {
        updateFilters({ status: v });
      }
    } else {
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

        <Segmented
          options={segmentOptions}
          value={activeView}
          onChange={onSegmentChange}
        />
      </div>

      <Space style={{ marginBottom: 16 }} wrap>
        <Input.Search
          placeholder="Search config number\u2026"
          allowClear
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onSearch={(value) => {
            setSearchInput(value);
            applyTopFilters({ search: value });
          }}
          style={{ width: 320 }}
        />

        <Select
          mode="multiple"
          allowClear
          showSearch
          placeholder="Family"
          value={familyInput}
          onChange={setFamilyInput}
          maxTagCount="responsive"
          style={{ width: 220 }}
          options={(options.families || []).map((s) => ({
            value: s,
            label: s,
          }))}
        />

        <Select
          mode="multiple"
          allowClear
          showSearch
          placeholder="Form Factor"
          value={formFactorInput}
          onChange={setFormFactorInput}
          maxTagCount="responsive"
          style={{ width: 220 }}
          options={(options.form_factors || []).map((s) => ({
            value: s,
            label: s,
          }))}
        />

        <Select
          mode="multiple"
          allowClear
          showSearch
          placeholder="Requestor"
          value={requestorInput}
          onChange={setRequestorInput}
          maxTagCount="responsive"
          style={{ width: 240 }}
          options={requestorOptions}
          filterOption={(input, option) =>
            (option?.label || "").toLowerCase().includes(input.toLowerCase())
          }
        />

        {showStatusColumn && (
          <Select
            mode="multiple"
            allowClear
            showSearch
            placeholder="Status"
            value={statusInput}
            onChange={setStatusInput}
            maxTagCount="responsive"
            style={{ width: 220 }}
            options={(options.statuses || STATUSES).map((s) => ({
              value: s,
              label: s,
            }))}
          />
        )}

        <Button
          type="primary"
          icon={<SearchOutlined />}
          onClick={() => applyTopFilters()}
        >
          Apply
        </Button>

        <Button onClick={handleReset}>Reset</Button>

        <Button icon={<ReloadOutlined />} onClick={() => loadData()}>
          Refresh
        </Button>
      </Space>

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
