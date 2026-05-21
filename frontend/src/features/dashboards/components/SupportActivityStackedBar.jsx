import { useEffect, useState } from "react";
import { Card, Col, Empty, Row, Segmented, Skeleton } from "antd";
import ChartInfoTooltip from "./ChartInfoTooltip";
import { Column } from "@ant-design/charts";
import { fetchSupportActivityBreakdown } from "../services/dashboard_service";
import { useDashboardFilters } from "../state/DashboardFiltersContext";

/**
 * Stacked bar: X = Support Activity, stack = Form Factor, Y = boards or builds.
 * Click a stack segment to toggle that Form Factor in the filter; click an
 * X-axis group to toggle the support activity. Activities are sorted by
 * total value (largest first).
 */
export default function SupportActivityStackedBar() {
  const { filters, toggleMulti } = useDashboardFilters();
  const [metric, setMetric] = useState("builds");
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchSupportActivityBreakdown(filters, metric)
      .then((d) => !cancelled && setData(d?.rows || []))
      .catch(() => !cancelled && setData([]))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [filters, metric]);

  // Sort the X-axis (support activities) by total value descending so the
  // tallest stack appears on the left.
  const totalsByActivity = data.reduce((acc, r) => {
    const key = r.support_activity;
    acc[key] = (acc[key] || 0) + (Number(r.value) || 0);
    return acc;
  }, {});
  const activityOrder = Object.entries(totalsByActivity)
    .sort((a, b) => b[1] - a[1])
    .map(([name]) => name);

  const chartData = data
    .map((r) => ({
      activity: r.support_activity,
      form_factor: r.form_factor,
      value: Number(r.value) || 0,
    }))
    .sort(
      (a, b) =>
        activityOrder.indexOf(a.activity) - activityOrder.indexOf(b.activity),
    );

  const config = {
    data: chartData,
    xField: "activity",
    yField: "value",
    colorField: "form_factor",
    stack: true,
    height: 320,
    scale: { x: { domain: activityOrder } },
    axis: { x: { labelAutoRotate: true } },
    tooltip: {
      title: (d) => d.activity,
      items: [
        {
          field: "value",
          valueFormatter: (v) => Math.round(v).toLocaleString(),
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
        <Row justify="space-between" align="middle">
          <Col>
            Number of Builds/Boards by Support Activity and Form Factor
            <ChartInfoTooltip title="Stacked counts of builds (or boards) grouped by support activity, segmented by form factor. Activities are sorted by total value (largest first)." />
          </Col>
          <Col>
            <Segmented
              size="small"
              value={metric}
              onChange={(v) => setMetric(v)}
              options={[
                { label: "Builds", value: "builds" },
                { label: "Boards", value: "boards" },
              ]}
            />
          </Col>
        </Row>
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
