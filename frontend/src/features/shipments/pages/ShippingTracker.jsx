import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Input,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from "antd";
import { ReloadOutlined, SearchOutlined } from "@ant-design/icons";
import { useShippingTable } from "@/features/shipments/hooks/useShippingTable";
import { fetchShippingFilterOptions } from "@/features/shipments/services/shipping_filter_options";
import { getServerColumnProps } from "@/shared/components/serverColumnFilter";
import { sortOrderFor } from "@/shared/hooks/usePaginatedTable";

const { Title } = Typography;

const STATUS_COLORS = {
  Scheduled: "processing",
  ShippedOut: "warning",
  Delivered: "success",
  Completed: "success",
};

const toCsv = (arr) => (Array.isArray(arr) && arr.length ? arr.join(",") : "");
const fromCsv = (s) => (s ? String(s).split(",").filter(Boolean) : []);

export default function ShippingTracker() {
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
  } = useShippingTable();

  const [options, setOptions] = useState({
    families: [],
    forwarders: [],
    handlers: [],
    recipients: [],
    statuses: [],
  });

  useEffect(() => {
    fetchShippingFilterOptions()
      .then((d) => setOptions(d || {}))
      .catch(() => {});
  }, []);

  // Buffered top-toolbar inputs — only push to server on Apply
  const [searchInput, setSearchInput] = useState(filters.search || "");
  const [familyInput, setFamilyInput] = useState(fromCsv(filters.family));
  const [forwarderInput, setForwarderInput] = useState(
    fromCsv(filters.forwarder)
  );
  const [handlerInput, setHandlerInput] = useState(fromCsv(filters.handler));
  const [recipientInput, setRecipientInput] = useState(
    fromCsv(filters.recipient)
  );
  const [statusInput, setStatusInput] = useState(fromCsv(filters.status));

  function applyTopFilters(overrides = {}) {
    updateFilters({
      search: searchInput,
      family: toCsv(familyInput),
      forwarder: toCsv(forwarderInput),
      handler: toCsv(handlerInput),
      recipient: toCsv(recipientInput),
      status: toCsv(statusInput),
      ...overrides,
    });
  }

  function handleReset() {
    setSearchInput("");
    setFamilyInput([]);
    setForwarderInput([]);
    setHandlerInput([]);
    setRecipientInput([]);
    setStatusInput([]);
    resetAllFilters();
  }

  const handlerOptions = useMemo(
    () =>
      (options.handlers || []).map((u) => ({
        label: u.label || u.full_name || u.email || `#${u.id}`,
        value: String(u.id),
      })),
    [options.handlers]
  );
  const recipientOptions = useMemo(
    () =>
      (options.recipients || []).map((u) => ({
        label: u.label || u.full_name || u.email || `#${u.id}`,
        value: String(u.id),
      })),
    [options.recipients]
  );

  const columns = [
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
      title: "Tracking #",
      dataIndex: "tracking_number",
      key: "tracking_number",
      sorter: { multiple: 3 },
      sortOrder: sortOrderFor(sorts, "tracking_number"),
      render: (v) => v || "\u2014",
    },
    {
      title: "Forwarder",
      dataIndex: "forwarder",
      key: "forwarder",
      sortOrder: sortOrderFor(sorts, "forwarder"),
      ...getServerColumnProps({
        dataIndex: "forwarder",
        title: "Forwarder",
        updateFilters,
        filters,
        filterOptions: options.forwarders || [],
        sortable: { multiple: 4 },
      }),
      render: (v) => v || "\u2014",
    },
    {
      title: "Quantity",
      dataIndex: "quantity",
      key: "quantity",
      width: 110,
      sorter: { multiple: 5 },
      sortOrder: sortOrderFor(sorts, "quantity"),
    },
    {
      title: "Ship Date",
      dataIndex: "ship_date",
      key: "ship_date",
      sorter: { multiple: 6 },
      sortOrder: sortOrderFor(sorts, "ship_date"),
      render: (v) => v || "\u2014",
    },
    {
      title: "ETA",
      dataIndex: "eta",
      key: "eta",
      sorter: { multiple: 7 },
      sortOrder: sortOrderFor(sorts, "eta"),
      render: (v) => v || "\u2014",
    },
    {
      title: "Delivery Date",
      dataIndex: "delivery_date",
      key: "delivery_date",
      sorter: { multiple: 8 },
      sortOrder: sortOrderFor(sorts, "delivery_date"),
      render: (v) => v || "\u2014",
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      width: 130,
      sortOrder: sortOrderFor(sorts, "status"),
      ...getServerColumnProps({
        dataIndex: "status",
        title: "Status",
        updateFilters,
        filters,
        filterOptions: options.statuses || [],
        sortable: { multiple: 9 },
      }),
      render: (s) => <Tag color={STATUS_COLORS[s] || "default"}>{s}</Tag>,
    },
    {
      title: "Handler",
      key: "handler",
      sortOrder: sortOrderFor(sorts, "handler"),
      ...getServerColumnProps({
        dataIndex: "handler",
        title: "Handler",
        updateFilters,
        filters,
        filterOptions: handlerOptions,
        sortable: { multiple: 10 },
      }),
      render: (_, r) => r.recipient_user?.full_name || "\u2014",
    },
    {
      title: "Recipients",
      key: "recipient",
      ...getServerColumnProps({
        dataIndex: "recipient",
        title: "Recipients",
        updateFilters,
        filters,
        filterOptions: recipientOptions,
      }),
      render: (_, r) => {
        const list = r.recipients || [];
        if (!list.length) return "\u2014";
        return list
          .map((u) => u.full_name)
          .filter(Boolean)
          .join(", ");
      },
    },
  ];

  return (
    <Card>
      <Title level={3}>Shipment Tracker</Title>

      <Space style={{ marginBottom: 16 }} wrap>
        <Input.Search
          placeholder="Search (config #, tracking, handler\u2026)"
          allowClear
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          onSearch={(value) => {
            setSearchInput(value);
            applyTopFilters({ search: value });
          }}
          style={{ width: 360 }}
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
          placeholder="Forwarder"
          value={forwarderInput}
          onChange={setForwarderInput}
          maxTagCount="responsive"
          style={{ width: 220 }}
          options={(options.forwarders || []).map((s) => ({
            value: s,
            label: s,
          }))}
        />

        <Select
          mode="multiple"
          allowClear
          showSearch
          placeholder="Handler"
          value={handlerInput}
          onChange={setHandlerInput}
          maxTagCount="responsive"
          style={{ width: 240 }}
          options={handlerOptions}
          filterOption={(input, option) =>
            (option?.label || "").toLowerCase().includes(input.toLowerCase())
          }
        />

        <Select
          mode="multiple"
          allowClear
          showSearch
          placeholder="Recipients"
          value={recipientInput}
          onChange={setRecipientInput}
          maxTagCount="responsive"
          style={{ width: 240 }}
          options={recipientOptions}
          filterOption={(input, option) =>
            (option?.label || "").toLowerCase().includes(input.toLowerCase())
          }
        />

        <Select
          mode="multiple"
          allowClear
          showSearch
          placeholder="Status"
          value={statusInput}
          onChange={setStatusInput}
          maxTagCount="responsive"
          style={{ width: 220 }}
          options={(options.statuses || []).map((s) => ({
            value: s,
            label: s,
          }))}
        />

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
        scroll={{ x: "max-content" }}
      />
    </Card>
  );
}
