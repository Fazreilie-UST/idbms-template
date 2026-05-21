import { useEffect, useMemo, useState } from "react";
import { Empty, Skeleton, Table } from "antd";
import { fetchSupplierComponentDetail } from "../services/dashboard_service";
import { useDashboardFilters } from "../state/DashboardFiltersContext";

/**
 * Detailed table for a selected component/slot.
 *
 *   <component_slot_supplier> | attr_1 | attr_2 | ... | Total boards | required_quantity | number of builds
 *
 * Attribute columns are derived dynamically from the response so each
 * component can have its own column set. The table is horizontally
 * scrollable to handle components with many attributes.
 */
export default function SupplierComponentDetailTable({ componentName, slotCode }) {
  const { filters } = useDashboardFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!componentName) return;
    let cancelled = false;
    setLoading(true);
    fetchSupplierComponentDetail(componentName, slotCode ?? null, filters)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setData(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [componentName, slotCode, filters]);

  const formatInt = (v) =>
    Number.isFinite(Number(v)) ? Math.round(Number(v)).toLocaleString() : "—";

  const supplierColumnTitle = useMemo(() => {
    const base = slotCode ? `${componentName}_${slotCode}` : componentName;
    return `${base || "Component"} supplier`;
  }, [componentName, slotCode]);

  const columns = useMemo(() => {
    const attrCols = (data?.columns ?? []).map((name) => ({
      title: name,
      dataIndex: ["attributes", name],
      key: `attr_${name}`,
      width: 140,
      render: (val) => (val === null || val === undefined || val === "" ? "—" : String(val)),
    }));

    return [
      {
        title: supplierColumnTitle,
        key: "supplier",
        dataIndex: "supplier",
        fixed: "left",
        width: 200,
        render: (val) => val || "Unknown",
      },
      ...attrCols,
      {
        title: "Total Boards",
        dataIndex: "boards",
        key: "boards",
        align: "right",
        width: 130,
        sorter: (a, b) => (a.boards || 0) - (b.boards || 0),
        render: formatInt,
      },
      {
        title: "Required Qty",
        dataIndex: "required_quantity",
        key: "required_quantity",
        align: "right",
        width: 130,
        sorter: (a, b) =>
          (a.required_quantity || 0) - (b.required_quantity || 0),
        render: formatInt,
      },
      {
        title: "# Builds",
        dataIndex: "builds",
        key: "builds",
        align: "right",
        width: 110,
        sorter: (a, b) => (a.builds || 0) - (b.builds || 0),
        render: formatInt,
      },
    ];
  }, [data, supplierColumnTitle]);

  if (loading) return <Skeleton active paragraph={{ rows: 4 }} />;

  const rows = data?.rows ?? [];
  if (!componentName || rows.length === 0) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={componentName ? "No data" : "Select a component"}
      />
    );
  }

  const dataSource = rows.map((r, idx) => ({ key: idx, ...r }));

  const totals = rows.reduce(
    (acc, r) => {
      acc.boards += Number(r.boards) || 0;
      acc.required_quantity += Number(r.required_quantity) || 0;
      acc.builds += Number(r.builds) || 0;
      return acc;
    },
    { boards: 0, required_quantity: 0, builds: 0 },
  );

  const attrColCount = data?.columns?.length ?? 0;

  return (
    <Table
      size="small"
      columns={columns}
      dataSource={dataSource}
      pagination={false}
      scroll={{ x: "max-content", y: 360 }}
      bordered
      sticky
      summary={() => (
        <Table.Summary fixed>
          <Table.Summary.Row style={{ fontWeight: 600, background: "#fafafa" }}>
            <Table.Summary.Cell index={0}>TOTAL</Table.Summary.Cell>
            {Array.from({ length: attrColCount }).map((_, i) => (
              <Table.Summary.Cell key={`a${i}`} index={1 + i} />
            ))}
            <Table.Summary.Cell index={1 + attrColCount} align="right">
              {formatInt(totals.boards)}
            </Table.Summary.Cell>
            <Table.Summary.Cell index={2 + attrColCount} align="right">
              {formatInt(totals.required_quantity)}
            </Table.Summary.Cell>
            <Table.Summary.Cell index={3 + attrColCount} align="right">
              {formatInt(totals.builds)}
            </Table.Summary.Cell>
          </Table.Summary.Row>
        </Table.Summary>
      )}
    />
  );
}
