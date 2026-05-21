import { useEffect, useMemo, useState } from "react";
import { Card, Empty, Skeleton, Table, Tag } from "antd";
import ChartInfoTooltip from "./ChartInfoTooltip";
import { fetchSiliconStepping } from "../services/dashboard_service";
import { useDashboardFilters } from "../state/DashboardFiltersContext";

/**
 * Table of builds by Silicon Stepping, sorted descending (top 5 highlighted).
 * Click a row -> toggles that stepping in the global filter set.
 */
export default function SiliconSteppingPie() {
  const { filters, toggleMulti } = useDashboardFilters();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchSiliconStepping(filters)
      .then((d) => !cancelled && setData(Array.isArray(d) ? d : []))
      .catch(() => !cancelled && setData([]))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [filters]);

  const rows = useMemo(() => {
    const sorted = [...data].sort(
      (a, b) => (Number(b.value) || 0) - (Number(a.value) || 0),
    );
    return sorted.map((d, idx) => ({
      key: d.label,
      rank: idx + 1,
      stepping: d.label,
      value: Number(d.value) || 0,
      isTop: idx < 5,
    }));
  }, [data]);

  const selected = filters.siliconSteppings || [];

  return (
    <Card
      title={
        <>
          Builds by Silicon Stepping
          <ChartInfoTooltip title="Distribution of builds across silicon stepping codes for the current filter scope. Click a slice to filter every widget on that stepping." />
        </>
      }
      size="small"
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 5 }} />
      ) : rows.length === 0 ? (
        <Empty description="No data" />
      ) : (
        <Table
          size="small"
          pagination={false}
          dataSource={rows}
          scroll={{ y: 260 }}
          sticky
          rowClassName={(r) => (r.isTop ? "" : "")}
          onRow={(r) => ({
            onClick: () => toggleMulti("siliconSteppings", r.stepping),
            style: { cursor: "pointer" },
          })}
          columns={[
            {
              title: "#",
              dataIndex: "rank",
              width: 50,
              render: (v, r) =>
                r.isTop ? <Tag color="gold">{v}</Tag> : v,
            },
            {
              title: "Stepping",
              dataIndex: "stepping",
              render: (v) =>
                selected.includes(v) ? <Tag color="processing">{v}</Tag> : v,
            },
            {
              title: "Builds",
              dataIndex: "value",
              align: "right",
              width: 100,
              render: (v) => v.toLocaleString(),
            },
          ]}
        />
      )}
    </Card>
  );
}
