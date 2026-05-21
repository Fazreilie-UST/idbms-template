import { useEffect, useMemo, useState } from "react";
import { Card, Col, Empty, Row, Skeleton, Typography } from "antd";
import ChartInfoTooltip from "./ChartInfoTooltip";
import { Bar, Pie } from "@ant-design/charts";
import { fetchFamilyAttributeBreakdown } from "../services/dashboard_service";
import { useDashboardFilters } from "../state/DashboardFiltersContext";

const { Text } = Typography;

/**
 * For every Family, render three small pies side-by-side:
 *   - Builds by Silicon Stepping
 *   - Builds by PCB Revision
 *   - Builds by HW Revision
 *
 * Same build-plan scope as Family × SKU breakdown (cancelled excluded by
 * default; respects the global Status filter).
 */
export default function FamilyAttributePieGrid() {
  const { filters } = useDashboardFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchFamilyAttributeBreakdown(filters)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setData(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [filters]);

  const families = data?.families ?? [];

  return (
    <Card
      title={
        <>
          Family × Attribute breakdown
          <ChartInfoTooltip title="Per-family pies showing the share of builds across silicon stepping, PCB revision, and HW revision. Click a slice to drill in on that attribute." />
        </>
      }
      size="small"
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 4 }} />
      ) : families.length === 0 ? (
        <Empty description="No data" />
      ) : (
        <Row gutter={[12, 12]}>
          {families.map((fam) => {
            const stepCount = (fam.silicon_steppings || []).length;
            // Bar chart grows with the number of stepping rows so labels stay
            // readable. The two pie charts use a fixed height so every family
            // card renders at a consistent size regardless of slice count.
            const barHeight = Math.max(180, stepCount * 28);
            const PIE_HEIGHT = 260;
            return (
              <Col xs={24} key={fam.family_code}>
                <Card size="small" type="inner" title={fam.family_code}>
                  <Row gutter={[12, 12]}>
                    <Col xs={24} md={8}>
                      <AttributeBar
                        title="Silicon Stepping"
                        slices={fam.silicon_steppings}
                        height={barHeight}
                      />
                    </Col>
                    <Col xs={24} md={8}>
                      <AttributePie
                        title="PCB Revision"
                        slices={fam.pcb_revisions}
                        height={PIE_HEIGHT}
                      />
                    </Col>
                    <Col xs={24} md={8}>
                      <AttributePie
                        title="HW Revision"
                        slices={fam.hw_revisions}
                        height={PIE_HEIGHT}
                      />
                    </Col>
                  </Row>
                </Card>
              </Col>
            );
          })}
        </Row>
      )}
    </Card>
  );
}

function AttributePie({ title, slices, height = 180 }) {
  const chartData = useMemo(
    () =>
      (slices || []).map((s) => ({
        type: s.label,
        value: Number(s.value) || 0,
      })),
    [slices],
  );

  const total = chartData.reduce((acc, d) => acc + d.value, 0);

  // Map label → build count so the legend can surface the quantity on hover
  // (and inline alongside each label).
  const countByLabel = useMemo(() => {
    const m = {};
    for (const d of chartData) m[d.type] = d.value;
    return m;
  }, [chartData]);

  return (
    <div>
      <Text strong style={{ fontSize: 12 }}>
        {title}
      </Text>
      <div>
        <Text type="secondary" style={{ fontSize: 12 }}>
          Total: {Math.round(total).toLocaleString()} builds
        </Text>
      </div>
      {chartData.length === 0 || total === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No data" />
      ) : (
        <Pie
          data={chartData}
          angleField="value"
          colorField="type"
          radius={1}
          height={height}
          legend={{
            color: {
              position: "bottom",
              itemLabelText: (d) => {
                const v = countByLabel[d.label] ?? 0;
                return `${d.label} (${Math.round(v).toLocaleString()})`;
              },
              // Show a tooltip when hovering a legend item so the exact
              // build count for that label stays visible.
              itemTooltip: (d) => {
                const v = countByLabel[d.label] ?? 0;
                return {
                  title: d.label,
                  items: [
                    {
                      name: "Builds",
                      value: `${Math.round(v).toLocaleString()}`,
                    },
                  ],
                };
              },
            },
          }}
          label={false}
          tooltip={{
            title: (d) => d.type,
            items: [
              {
                field: "value",
                valueFormatter: (v) =>
                  `${Math.round(v).toLocaleString()} builds`,
              },
            ],
          }}
          interactions={[{ type: "element-active" }]}
        />
      )}
    </div>
  );
}

function AttributeBar({ title, slices, height }) {
  const chartData = useMemo(
    () =>
      (slices || [])
        .map((s) => ({
          stepping: s.label,
          value: Number(s.value) || 0,
        }))
        .sort((a, b) => b.value - a.value),
    [slices],
  );

  const total = chartData.reduce((acc, d) => acc + d.value, 0);

  return (
    <div>
      <Text strong style={{ fontSize: 12 }}>
        {title}
      </Text>
      <div>
        <Text type="secondary" style={{ fontSize: 12 }}>
          Total: {Math.round(total).toLocaleString()} builds
        </Text>
      </div>
      {chartData.length === 0 || total === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No data" />
      ) : (
        <Bar
          data={chartData}
          xField="stepping"
          yField="value"
          height={height ?? Math.max(180, chartData.length * 28)}
          legend={false}
          label={{
            text: "value",
            position: "right",
            style: { fontSize: 11 },
          }}
          tooltip={{
            title: (d) => d.stepping,
            items: [
              {
                field: "value",
                valueFormatter: (v) =>
                  `${Math.round(v).toLocaleString()} builds`,
              },
            ],
          }}
          interactions={[{ type: "element-active" }]}
        />
      )}
    </div>
  );
}
