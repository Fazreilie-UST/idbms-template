import { useEffect, useMemo, useState } from "react";
import { Card, Col, Empty, Row, Segmented, Skeleton, Typography } from "antd";
import ChartInfoTooltip from "./ChartInfoTooltip";
import { Pie } from "@ant-design/charts";
import { fetchFamilyBreakdown } from "../services/dashboard_service";
import { useDashboardFilters } from "../state/DashboardFiltersContext";

const { Text } = Typography;

/**
 * Grid of donut charts — one per Family, slices = Form Factors.
 * Metric toggle: Boards | Builds.
 * Clicking a slice toggles that Form Factor in the global filter (cross-filter).
 */
export default function FamilyDonutGrid() {
  const { filters, toggleMulti } = useDashboardFilters();
  const [metric, setMetric] = useState("boards");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchFamilyBreakdown(filters, metric)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setData(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [filters, metric]);

  const families = data?.families ?? [];

  return (
    <Card
      title={
        <Row justify="space-between" align="middle">
          <Col>
            Family × Form Factor breakdown
            <ChartInfoTooltip title="Per-family donut showing the share of builds (or boards) across Form Factors within the current filter scope." />
          </Col>
          <Col>
            <Segmented
              size="small"
              value={metric}
              onChange={(v) => setMetric(v)}
              options={[
                { label: "Boards", value: "boards" },
                { label: "Builds", value: "builds" },
              ]}
            />
          </Col>
        </Row>
      }
      size="small"
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 4 }} />
      ) : families.length === 0 ? (
        <Empty description="No data" />
      ) : (
        <Row gutter={[12, 12]}>
          {families.map((fam) => (
            <Col xs={24} sm={12} md={8} lg={6} key={fam.family_code}>
              <Card size="small" type="inner" title={fam.family_code}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  Total: {Math.round(fam.total).toLocaleString()}
                </Text>
                <FamilyDonut
                  family={fam}
                  metric={metric}
                  onSliceClick={(formFactor) => toggleMulti("formFactors", formFactor)}
                />
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </Card>
  );
}

function FamilyDonut({ family, metric, onSliceClick }) {
  const chartData = useMemo(
    () =>
      (family.form_factors || []).map((s) => ({
        type: s.form_factor,
        name: s.form_factor,
        value: Number(s.value) || 0,
      })),
    [family],
  );

  if (chartData.length === 0 || chartData.every((d) => d.value === 0)) {
    return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No data" />;
  }

  const config = {
    data: chartData,
    angleField: "value",
    colorField: "type",
    radius: 1,
    height: 180,
    legend: false,
    label: false,
    tooltip: {
      title: (d) => d.name || d.type,
      items: [
        {
          field: "value",
          valueFormatter: (v) =>
            `${Math.round(v).toLocaleString()} ${metric === "boards" ? "boards" : "builds"}`,
        },
      ],
    },
    interactions: [{ type: "element-active" }],
    onReady: (plot) => {
      try {
        plot.chart.on("interval:click", (evt) => {
          const datum = evt?.data?.data;
          if (datum?.type) onSliceClick(datum.type);
        });
      } catch {
        /* chart instance shape varies between versions */
      }
    },
  };

  return <Pie {...config} />;
}
