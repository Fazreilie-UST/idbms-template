import { useEffect, useMemo, useState } from "react";
import { Card, Empty, Skeleton } from "antd";
import ChartInfoTooltip from "./ChartInfoTooltip";
import { Column } from "@ant-design/charts";
import { fetchRequiredQuantityTop } from "../services/dashboard_service";
import { useDashboardFilters } from "../state/DashboardFiltersContext";

/**
 * Stacked vertical bar of required_quantity per Family, stacked by Form Factor
 * (same chart style as the Support Activity × Form Factor widget). Click a stack
 * segment to toggle that Form Factor in the global filter.
 */
export default function RequiredQuantityTopBar() {
  const { filters, toggleMulti } = useDashboardFilters();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchRequiredQuantityTop(filters, 50)
      .then((d) => !cancelled && setRows(Array.isArray(d) ? d : []))
      .catch(() => !cancelled && setRows([]))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [filters]);

  const chartData = useMemo(
    () =>
      rows.map((r) => ({
        family_code: r.family_code,
        form_factor: r.form_factor,
        value: Number(r.required_quantity) || 0,
      })),
    [rows]
  );

  const config = {
    data: chartData,
    xField: "family_code",
    yField: "value",
    colorField: "form_factor",
    stack: true,
    height: 320,
    axis: { x: { labelAutoRotate: true } },
    tooltip: {
      title: (d) => d.family_code,
      items: [
        {
          field: "value",
          valueFormatter: (v) => `${Math.round(v).toLocaleString()} units`,
        },
      ],
    },
    onReady: (plot) => {
      try {
        plot.chart.on("interval:click", (evt) => {
          const d = evt?.data?.data;
          if (d?.form_factor) toggleMulti("formFactors", d.form_factor);
        });
      } catch {
        /* ignore */
      }
    },
  };

  return (
    <Card
      title={
        <>
          Required Build Quantity by Family
          <ChartInfoTooltip title="Sum of the required board quantity for each family within the current filter scope." />
        </>
      }
      size="small"
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 6 }} />
      ) : chartData.length === 0 ? (
        <Empty description="No data" />
      ) : (
        <Column {...config} />
      )}
    </Card>
  );
}
