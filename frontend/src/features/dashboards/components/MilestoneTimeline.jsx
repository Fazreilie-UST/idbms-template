import { useEffect, useState } from "react";
import { Card, Col, Empty, Row, Segmented, Skeleton } from "antd";
import ChartInfoTooltip from "./ChartInfoTooltip";
import { Column } from "@ant-design/charts";
import { fetchMilestoneTimeline } from "../services/dashboard_service";
import { useDashboardFilters } from "../state/DashboardFiltersContext";

/**
 * Monthly bar chart of Milestone build counts (build_start_date based).
 * Click a bar -> filters Year to that bar's year.
 */
export default function MilestoneTimeline() {
  const { filters, setYear } = useDashboardFilters();
  const [metric, setMetric] = useState("builds");
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchMilestoneTimeline(filters, metric)
      .then((d) => !cancelled && setData(Array.isArray(d) ? d : []))
      .catch(() => !cancelled && setData([]))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [filters, metric]);

  const chartData = data.map((d) => ({
    period: d.period,
    value: Number(d.count) || 0,
  }));

  const valueSuffix = metric === "boards" ? "boards" : "milestone builds";

  const config = {
    data: chartData,
    xField: "period",
    yField: "value",
    height: 260,
    axis: { x: { labelAutoRotate: true } },
    label: { text: "value", position: "top", style: { fontSize: 11 } },
    tooltip: {
      title: (d) => d.period,
      items: [
        {
          channel: "y",
          valueFormatter: (v) => `${Math.round(v).toLocaleString()} ${valueSuffix}`,
        },
      ],
    },
    onReady: (plot) => {
      try {
        plot.chart.on("interval:click", (evt) => {
          const d = evt?.data?.data;
          if (d?.period) {
            const [y] = d.period.split("-");
            if (y) setYear(Number(y));
          }
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
            Milestone Builds Timeline (monthly)
            <ChartInfoTooltip title="Monthly count of milestone builds (or boards) over the current filter scope." />
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
        <Skeleton active paragraph={{ rows: 5 }} />
      ) : chartData.length === 0 ? (
        <Empty description="No milestone builds in scope" />
      ) : (
        <Column {...config} />
      )}
    </Card>
  );
}
