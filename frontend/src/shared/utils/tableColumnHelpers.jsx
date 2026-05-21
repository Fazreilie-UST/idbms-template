import { Button, Input, Space } from "antd";
import { SearchOutlined } from "@ant-design/icons";

/**
 * Build an Ant Design column `filterDropdown` config that renders an
 * inline text-search box for the column. Filtering is performed
 * client-side against the value returned by `getValue(record)`, so this
 * only filters whatever rows are currently loaded (e.g. the current page
 * for server-paginated tables).
 *
 * @param {(record: any) => string | number | null | undefined} getValue
 * @param {string} [placeholder]
 */
export function textSearchFilter(getValue, placeholder = "Search") {
  return {
    filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
      <div style={{ padding: 8 }} onKeyDown={(e) => e.stopPropagation()}>
        <Input
          autoFocus
          allowClear
          placeholder={placeholder}
          value={selectedKeys[0]}
          onChange={(e) =>
            setSelectedKeys(e.target.value ? [e.target.value] : [])
          }
          onPressEnter={() => confirm()}
          style={{ marginBottom: 8, display: "block", width: 200 }}
          prefix={<SearchOutlined />}
        />
        <Space>
          <Button
            type="primary"
            size="small"
            onClick={() => confirm()}
            icon={<SearchOutlined />}
            style={{ width: 90 }}
          >
            Search
          </Button>
          <Button
            size="small"
            onClick={() => {
              clearFilters?.();
              confirm();
            }}
            style={{ width: 90 }}
          >
            Reset
          </Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered) => (
      <SearchOutlined style={{ color: filtered ? "#1677ff" : undefined }} />
    ),
    onFilter: (value, record) => {
      const v = getValue(record);
      if (v === null || v === undefined) return false;
      return String(v).toLowerCase().includes(String(value).toLowerCase());
    },
  };
}

/**
 * Build a sorter for a numeric-or-null field. Null/undefined sort last
 * regardless of direction.
 */
export function numericSorter(getValue) {
  return (a, b) => {
    const av = getValue(a);
    const bv = getValue(b);
    const aMissing = av === null || av === undefined || Number.isNaN(av);
    const bMissing = bv === null || bv === undefined || Number.isNaN(bv);
    if (aMissing && bMissing) return 0;
    if (aMissing) return 1;
    if (bMissing) return -1;
    return Number(av) - Number(bv);
  };
}

/**
 * Build a locale-aware sorter for a string field. Null/undefined sort last.
 */
export function stringSorter(getValue) {
  return (a, b) => {
    const av = getValue(a);
    const bv = getValue(b);
    const aMissing = av === null || av === undefined || av === "";
    const bMissing = bv === null || bv === undefined || bv === "";
    if (aMissing && bMissing) return 0;
    if (aMissing) return 1;
    if (bMissing) return -1;
    return String(av).localeCompare(String(bv), undefined, {
      numeric: true,
      sensitivity: "base",
    });
  };
}

/**
 * Build a sorter for a date-like field (ISO string, epoch ms, or Date).
 * Null/undefined/invalid sort last.
 */
export function dateSorter(getValue) {
  return (a, b) => {
    const av = getValue(a);
    const bv = getValue(b);
    const at = av ? new Date(av).getTime() : NaN;
    const bt = bv ? new Date(bv).getTime() : NaN;
    const aMissing = Number.isNaN(at);
    const bMissing = Number.isNaN(bt);
    if (aMissing && bMissing) return 0;
    if (aMissing) return 1;
    if (bMissing) return -1;
    return at - bt;
  };
}

/**
 * Build an `filters` array for AntD column from a list of distinct values.
 */
export function valueFilters(values) {
  return values.map((v) => ({ text: v, value: v }));
}
