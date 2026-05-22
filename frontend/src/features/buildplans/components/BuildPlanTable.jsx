import { useMemo, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  Table,
  Input,
  Button,
  Space,
  Drawer,
  Checkbox,
  Tabs,
  Tag,
  Select,
} from "antd";
import {
  SearchOutlined,
  SettingOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import "@/features/buildplans/components/BuildPlanTable.css";

const DEFAULT_VISIBLE_COLUMNS = [
  "build_plan_id",
  "config_number",
  "revision",
  "support_activity",
  "build_description",
  "build_notes",
  "status",
  "product_code",
  "year",
];

const EMPTY_FILTER_OPTIONS = {
  family_code: [],
  form_factor: [],
  support_activity: [],
  build_description: [],
  build_notes: [],
  status: [],
  year: [],
  silicon_stepping: [],
};

function safeOptions(values) {
  return (values || [])
    .filter((value) => value !== null && value !== undefined && value !== "")
    .map((value) => ({
      label: String(value),
      value: String(value),
    }));
}

function renderBuildNotes(value) {
  let notes = [];

  if (Array.isArray(value)) {
    notes = value;
  } else if (typeof value === "string") {
    notes = value
      .replace(/^{|}$/g, "")
      .split(",")
      .map((item) => item.trim())
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

function getServerColumnProps({
  dataIndex,
  title,
  updateFilters,
  filters,
  filterOptions = [],
  sortMultiple,
}) {
  return {
    sorter: { multiple: sortMultiple },
    filteredValue: filters?.[dataIndex] ? [filters[dataIndex]] : null,

    filterDropdown: ({
      selectedKeys,
      setSelectedKeys,
      confirm,
      clearFilters,
    }) => {
      const selectedValues = selectedKeys[0]
        ? String(selectedKeys[0]).split(",")
        : [];

      return (
        <div style={{ padding: 8, width: 280 }}>
          <Input
            placeholder={`Search ${title}`}
            allowClear
            value={
              typeof selectedKeys[0] === "string" &&
              !selectedKeys[0].includes(",")
                ? selectedKeys[0]
                : ""
            }
            onChange={(e) => {
              const value = e.target.value;
              setSelectedKeys(value ? [value] : []);
            }}
            onPressEnter={() => {
              updateFilters({ [dataIndex]: selectedKeys[0] || "" });
              confirm();
            }}
            style={{ marginBottom: 8 }}
          />

          <Select
            mode="multiple"
            allowClear
            showSearch
            placeholder={`Filter ${title}`}
            value={selectedValues}
            style={{ width: "100%", marginBottom: 8 }}
            maxTagCount="responsive"
            options={safeOptions(filterOptions)}
            onChange={(values) => {
              setSelectedKeys(values.length ? [values.join(",")] : []);
            }}
          />

          <Space>
            <Button
              type="primary"
              size="small"
              icon={<SearchOutlined />}
              onClick={() => {
                updateFilters({ [dataIndex]: selectedKeys[0] || "" });
                confirm();
              }}
            >
              Apply
            </Button>

            <Button
              size="small"
              onClick={() => {
                clearFilters?.();
                setSelectedKeys([]);
                updateFilters({ [dataIndex]: "" });
                confirm();
              }}
            >
              Reset
            </Button>
          </Space>
        </div>
      );
    },

    filterIcon: <SearchOutlined />,
  };
}

function ExpandedBuildPlanRow({ record }) {
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

  return (
    <div style={{ background: "#f5f5f5", padding: "1rem 2rem 2rem 2rem", width: "70vw", marginLeft: "4rem" }}>
      <Tabs
        defaultActiveKey="components"
        items={[
          {
            key: "components",
            label: "Key Components",
            children: (
              <Table
                rowKey={(row) =>
                  `${row.component_name}-${row.component_slot}-${row.supplier || ""}`
                }
                size="small"
                columns={componentColumns}
                dataSource={record.components || []}
                pagination={false}
              />
            ),
          },
          {
            key: "tests",
            label: "Tests",
            children: (
              <Table
                rowKey={(row) =>  `${row.test_name}-${row.test_detail || ""}`}
                size="small"
                columns={testColumns}
                dataSource={record.tests || []}
                pagination={false}
              />
            ),
          },
          {
            key: "orders",
            label: "Build Requests",
            children: (
              <Table
                rowKey="build_request_id"
                size="small"
                columns={orderColumns}
                dataSource={record.build_requests || []}
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
            label: "Warehouse Quantities",
            children: (
              <Table
                rowKey="warehouse_id"
                size="small"
                columns={warehouseColumns}
                dataSource={record.warehouses || []}
                pagination={false}
              />
            ),
          },
          {
            key: "shipments",
            label: `Shipments (${(record.shipments || []).length})`,
            children: (
              <Table
                rowKey="shipment_id"
                size="small"
                columns={shipmentColumns}
                dataSource={record.shipments || []}
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
            ),
          },
        ]}
      />
    </div>
  );
}

export default function BuildPlanTable({
  rows,
  loading,
  pagination,
  filters,
  filterOptions = EMPTY_FILTER_OPTIONS,
  updateFilters,
  resetAllFilters,
  handleTableChange,
  reload,
  selectable = false,
  selectedRowKeys = [],
  onSelectionChange,
  toolbarExtra = null,
  hideStatusColumn = false,
}) {
  const [columnDrawerOpen, setColumnDrawerOpen] = useState(false);
  const [visibleColumns, setVisibleColumns] = useState(DEFAULT_VISIBLE_COLUMNS);
  const [expandedRowKeys, setExpandedRowKeys] = useState([]);
  const [tableKey, setTableKey] = useState(0);

  const navigate = useNavigate();
  const location = useLocation();
  const buildPlanViewBase = location.pathname.startsWith("/build-plan-tracker")
    ? "/build-plan-tracker"
    : "/pm/build-plans";

  const [searchInput, setSearchInput] = useState(filters?.search || "");
  const [familyInput, setFamilyInput] = useState(
    filters?.family_code ? String(filters.family_code).split(",") : []
  );
  const [formFactorInput, setFormFactorInput] = useState(
    filters?.form_factor ? String(filters.form_factor).split(",") : []
  );
  const [statusInput, setStatusInput] = useState(
    filters?.status ? String(filters.status).split(",") : []
  );

  const resolvedFilterOptions = {
    ...EMPTY_FILTER_OPTIONS,
    ...(filterOptions || {}),
  };

  const allColumns = useMemo(
    () => [
      {
        title: "ID",
        dataIndex: "build_plan_id",
        key: "build_plan_id",
        sorter: { multiple: 1 },
        width: 80,
      },
      {
        title: "Family",
        dataIndex: "family_code",
        key: "family_code",
        ...getServerColumnProps({
          dataIndex: "family_code",
          title: "Family",
          updateFilters,
          filters,
          filterOptions: filterOptions?.family_code || [],
          sortMultiple: 7,
        }),
      },
      {
        title: "Form Factor",
        dataIndex: "form_factor",
        key: "form_factor",
        ...getServerColumnProps({
          dataIndex: "form_factor",
          title: "Form Factor",
          updateFilters,
          filters,
          filterOptions: filterOptions?.form_factor || [],
          sortMultiple: 8,
        }),
      },
      {
        title: "Config Number",
        dataIndex: "config_number",
        key: "config_number",
        ...getServerColumnProps({
          dataIndex: "config_number",
          title: "Config Number",
          updateFilters,
          filters,
          filterOptions: filterOptions?.config_number || [],
          sortMultiple: 2,
        }),
        render: (value, record) => (
          <Button
            type="link"
            style={{ padding: 0 }}
            onClick={(event) => {
              event.stopPropagation();
              navigate(`${buildPlanViewBase}/${record.build_plan_id}`);
            }}
          >
            {value || "-"}
          </Button>
        ),
      },
      {
        title: "Revision",
        dataIndex: "revision",
        key: "revision",
        sorter: { multiple: 14 },
      },
      {
        title: "Support Activity",
        dataIndex: "support_activity",
        key: "support_activity",
        ...getServerColumnProps({
          dataIndex: "support_activity",
          title: "Support Activity",
          updateFilters,
          filters,
          filterOptions: filterOptions?.support_activity || [],
          sortMultiple: 3,
        }),
      },
      {
        title: "Build Description",
        dataIndex: "build_description",
        key: "build_description",
        ...getServerColumnProps({
          dataIndex: "build_description",
          title: "Build Description",
          updateFilters,
          filters,
          filterOptions: filterOptions?.build_description || [],
          sortMultiple: 4,
        }),
      },
      {
        title: "Build Notes",
        dataIndex: "build_notes",
        key: "build_notes",
        ...getServerColumnProps({
          dataIndex: "build_notes",
          title: "Build Notes",
          updateFilters,
          filters,
          filterOptions: filterOptions?.build_notes || [],
          sortMultiple: 5,
        }),
        render: renderBuildNotes,
      },
      {
        title: "Status",
        dataIndex: "status",
        key: "status",
        ...getServerColumnProps({
          dataIndex: "status",
          title: "Status",
          updateFilters,
          filters,
          filterOptions: filterOptions?.status || [],
          sortMultiple: 6,
        }),
        render: (value) => <Tag>{value || "-"}</Tag>,
      },
      {
        title: "Product Code",
        dataIndex: "product_code",
        key: "product_code",
        ...getServerColumnProps({
          dataIndex: "product_code",
          title: "Product Code",
          updateFilters,
          filters,
          filterOptions: filterOptions?.product_code || [],
          sortMultiple: 9,
        }),
      },
      {
        title: "MM Number",
        dataIndex: "mm_number",
        key: "mm_number",
        ...getServerColumnProps({
          dataIndex: "mm_number",
          title: "MM Number",
          updateFilters,
          filters,
          filterOptions: filterOptions?.mm_number || [],
          sortMultiple: 10,
        }),
      },
      {
        title: "TA Number",
        dataIndex: "ta_number",
        key: "ta_number",
        ...getServerColumnProps({
          dataIndex: "ta_number",
          title: "TA Number",
          updateFilters,
          filters,
          filterOptions: filterOptions?.ta_number || [],
          sortMultiple: 11,
        }),
      },
      {
        title: "PBA Number",
        dataIndex: "pba_number",
        key: "pba_number",
        ...getServerColumnProps({
          dataIndex: "pba_number",
          title: "PBA Number",
          updateFilters,
          filters,
          filterOptions: filterOptions?.pba_number || [],
          sortMultiple: 12,
        }),
      },
      {
        title: "AS Number",
        dataIndex: "as_number",
        key: "as_number",
        ...getServerColumnProps({
          dataIndex: "as_number",
          title: "AS Number",
          updateFilters,
          filters,
          filterOptions: filterOptions?.as_number || [],
          sortMultiple: 13,
        }),
      },
      {
        title: "Build Start Date",
        dataIndex: "build_start_date",
        key: "build_start_date",
        sorter: { multiple: 15 },
      },
      {
        title: "Ship Date",
        dataIndex: "ship_date",
        key: "ship_date",
        sorter: { multiple: 16 },
      },
      {
        title: "Required Qty",
        dataIndex: "required_quantity",
        key: "required_quantity",
        sorter: { multiple: 17 },
      },
      {
        title: "Estimated Yield",
        dataIndex: "estimated_yield",
        key: "estimated_yield",
        sorter: { multiple: 18 },
      },
      {
        title: "Year",
        dataIndex: "year",
        key: "year",
        ...getServerColumnProps({
          dataIndex: "year",
          title: "Year",
          updateFilters,
          filters,
          filterOptions: filterOptions?.year || [],
          sortMultiple: 19,
        }),
      },
    ],
    [filterOptions, updateFilters, filters, navigate, buildPlanViewBase]
  );

  const columns = allColumns
    .filter((col) => visibleColumns.includes(col.key))
    .filter((col) => !(hideStatusColumn && col.key === "status"));

  function onTableChange(paginationInfo, tableFilters, sorter) {
    handleTableChange(paginationInfo, tableFilters, sorter);
  }

  function applyTopFilters(overrides = {}) {
    const patch = {
      search: searchInput,
      family_code: familyInput.join(","),
      form_factor: formFactorInput.join(","),
      ...overrides,
    };
    if (!hideStatusColumn) {
      patch.status = statusInput.join(",");
    }
    updateFilters(patch);
  }

  return (
    <>
      <Space style={{ marginBottom: 16 }} wrap>
        <Input.Search
          placeholder="Search config, product, MM, TA, PBA, AS..."
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
          onChange={(values) => setFamilyInput(values)}
          maxTagCount="responsive"
          style={{ width: 220 }}
          options={safeOptions(resolvedFilterOptions.family_code)}
        />

        <Select
          mode="multiple"
          allowClear
          showSearch
          placeholder="Form Factor"
          value={formFactorInput}
          onChange={(values) => setFormFactorInput(values)}
          maxTagCount="responsive"
          style={{ width: 220 }}
          options={safeOptions(resolvedFilterOptions.form_factor)}
        />

        {!hideStatusColumn && (
          <Select
            mode="multiple"
            allowClear
            showSearch
            placeholder="Status"
            value={statusInput}
            onChange={(values) => setStatusInput(values)}
            maxTagCount="responsive"
            style={{ width: 220 }}
            options={safeOptions(resolvedFilterOptions.status)}
          />
        )}

        <Button type="primary" icon={<SearchOutlined />} onClick={applyTopFilters}>
          Apply
        </Button>

        <Button
          onClick={() => {
            setSearchInput("");
            setFamilyInput([]);
            setFormFactorInput([]);
            setStatusInput([]);
            setExpandedRowKeys([]);
            setTableKey((k) => k + 1);
            resetAllFilters();
          }}
        >
          Reset
        </Button>

        <Button icon={<ReloadOutlined />} onClick={reload}>
          Refresh
        </Button>

        <Button icon={<SettingOutlined />} onClick={() => setColumnDrawerOpen(true)}>
          Columns
        </Button>

        {toolbarExtra ? (
          <div style={{ marginLeft: "auto" }}>{toolbarExtra}</div>
        ) : null}
      </Space>

    <Table
        key={tableKey}
        bordered
        rowKey="build_plan_id"
        loading={loading}
        columns={columns}
        dataSource={rows}
        onChange={onTableChange}
        rowClassName={() => "clickable-build-plan-row"}
        rowSelection={
          selectable
            ? {
                selectedRowKeys,
                onChange: (keys) => onSelectionChange?.(keys),
                preserveSelectedRowKeys: true,
              }
            : undefined
        }
        expandable={{
            expandedRowKeys,
            expandedRowRender: (record) => (
            <ExpandedBuildPlanRow record={record} />
            ),
            expandRowByClick: true,

            // HIDE THE + COLUMN
            showExpandColumn: false,

            onExpand: (expanded, record) => {
            const key = record.build_plan_id;

            setExpandedRowKeys((prev) =>
                expanded
                ? [...prev, key]
                : prev.filter((item) => item !== key)
            );
            },
        }}
        scroll={{ x: "max-content" }}
        pagination={{
            current: pagination.page,
            pageSize: pagination.page_size,
            total: pagination.total,
            showSizeChanger: true,
            pageSizeOptions: [10, 20, 50, 100],
            showTotal: (total) => `Total ${total} build plans`,
        }}
    />

      <Drawer
        title="Column Visibility"
        open={columnDrawerOpen}
        onClose={() => setColumnDrawerOpen(false)}
        size={360}
        extra={
          <Button onClick={() => setVisibleColumns(DEFAULT_VISIBLE_COLUMNS)}>
            Reset
          </Button>
        }
      >
        <Space orientation="vertical">
          <Checkbox
            checked={visibleColumns.length === allColumns.length}
            onChange={(e) => {
              if (e.target.checked) {
                setVisibleColumns(allColumns.map((col) => col.key));
              } else {
                setVisibleColumns([]);
              }
            }}
          >
            Show all
          </Checkbox>

          {allColumns
            .filter((col) => !(hideStatusColumn && col.key === "status"))
            .map((col) => (
            <Checkbox
              key={col.key}
              checked={visibleColumns.includes(col.key)}
              onChange={(e) => {
                if (e.target.checked) {
                  setVisibleColumns((prev) => [...prev, col.key]);
                } else {
                  setVisibleColumns((prev) =>
                    prev.filter((key) => key !== col.key)
                  );
                }
              }}
            >
              {col.title}
            </Checkbox>
          ))}
        </Space>
      </Drawer>
    </>
  );
}