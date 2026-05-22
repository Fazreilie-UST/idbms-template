import { Button, Input, Select, Space } from "antd";
import { SearchOutlined } from "@ant-design/icons";

export function safeOptions(values) {
  return (values || [])
    .filter((value) => value !== null && value !== undefined && value !== "")
    .map((value) => {
      if (typeof value === "object" && "value" in value) {
        return { label: String(value.label ?? value.value), value: value.value };
      }
      return { label: String(value), value: String(value) };
    });
}

/**
 * Build Ant Design Table column props that render a per-column filter
 * dropdown (free-text search + multi-select) wired to a server-side
 * filter map. Use with `usePaginatedTable`.
 *
 * @param {object} args
 * @param {string} args.dataIndex - key used in the filters object
 * @param {string} args.title - display label for the placeholder
 * @param {(patch: object) => void} args.updateFilters
 * @param {Record<string, string>} args.filters - current filters from the hook
 * @param {Array} [args.filterOptions] - distinct values for the multi-select
 * @param {boolean|number|object} [args.sortable] - sorter prop passthrough
 */
export function getServerColumnProps({
  dataIndex,
  filterKey,
  title,
  updateFilters,
  filters,
  filterOptions = [],
  sortable,
}) {
  const key = filterKey || dataIndex;
  const props = {
    filteredValue: filters?.[key] ? [filters[key]] : null,
    filterDropdown: ({ selectedKeys, setSelectedKeys, confirm, clearFilters }) => {
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
              updateFilters({ [key]: selectedKeys[0] || "" });
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
                updateFilters({ [key]: selectedKeys[0] || "" });
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
                updateFilters({ [key]: "" });
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
  if (sortable !== undefined) {
    props.sorter = sortable;
  }
  return props;
}
