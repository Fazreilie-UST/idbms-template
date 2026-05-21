import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Card,
  Col,
  Empty,
  Row,
  Select,
  Skeleton,
  Table,
  Typography,
} from "antd";
import { Pie } from "@ant-design/charts";
import {
  fetchFamilyComparison,
  fetchLookups,
} from "../services/dashboard_service";
import { useDashboardFilters } from "../state/DashboardFiltersContext";

const { Text } = Typography;

/**
 * Per-family comparison: pick a family, see one row per Form Factor with:
 *   - a Silicon Stepping pie
 *   - a PCB Revision pie
 *   - totals (builds, boards)
 * Plus a combined comparison table at the bottom listing the dominant
 * Si Stepping / PCB Revision per Form Factor.
 */
export default function FamilyComparisonPanel() {
  const { filters } = useDashboardFilters();
  const [families, setFamilies] = useState([]);
  const [selected, setSelected] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  // Auto-pick the first family from the filter set if exactly one is chosen.
  useEffect(() => {
    if (filters.familyCodes?.length === 1) {
      setSelected(filters.familyCodes[0]);
    }
  }, [filters.familyCodes]);

  // Family dropdown (independent of the main filter so user can compare any).
  useEffect(() => {
    let cancelled = false;
    fetchLookups()
      .then((d) => {
        if (cancelled) return;
        const opts = (d?.families || []).map((f) => {
          const code = f.label.split(" - ")[0];
          return { value: code, label: f.label };
        });
        setFamilies(opts);
        if (!selected && opts.length > 0) setSelected(opts[0].value);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
    // intentionally only on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    setLoading(true);
    fetchFamilyComparison(selected, filters)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setData(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [selected, filters]);

  const formFactors = data?.form_factors ?? [];

  const tableRows = useMemo(
    () =>
      formFactors.map((s) => ({
        key: s.form_factor,
        form_factor: s.form_factor,
        si_stepping: dominant(s.silicon_steppings),
        pcb_revision: dominant(s.pcb_revisions),
        builds: s.total_builds,
        boards: Math.round(s.total_boards),
      })),
    [formFactors],
  );

  return (
    <Card
      title={
        <Row justify="space-between" align="middle" gutter={8}>
          <Col>Per-Family Comparison</Col>
          <Col flex="240px">
            <Select
              size="small"
              showSearch
              placeholder="Select a Family"
              value={selected}
              onChange={setSelected}
              options={families}
              optionFilterProp="label"
              style={{ width: "100%" }}
            />
          </Col>
        </Row>
      }
      size="small"
    >
      {!selected ? (
        <Alert type="info" message="Select a Family to compare its Form Factors." />
      ) : loading ? (
        <Skeleton active paragraph={{ rows: 6 }} />
      ) : formFactors.length === 0 ? (
        <Empty description="No Form Factors match current filters" />
      ) : (
        <>
          <Row gutter={[12, 12]}>
            {formFactors.map((s) => (
              <Col xs={24} md={12} xl={8} key={s.form_factor}>
                <Card size="small" type="inner" title={s.form_factor}>
                  <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
                    <Tag count={s.total_builds} label="builds" />
                    <Tag
                      count={Math.round(s.total_boards)}
                      label="boards"
                    />
                  </div>
                  <Row gutter={6} style={{ marginTop: 8 }}>
                    <Col span={12}>
                      <MiniPie
                        title="Si Stepping"
                        data={s.silicon_steppings}
                      />
                    </Col>
                    <Col span={12}>
                      <MiniPie title="PCB Revision" data={s.pcb_revisions} />
                    </Col>
                  </Row>
                </Card>
              </Col>
            ))}
          </Row>

          <Card
            size="small"
            type="inner"
            title="Comparison Table"
            style={{ marginTop: 12 }}
          >
            <Table
              size="small"
              pagination={false}
              dataSource={tableRows}
              columns={[
                { title: "Form Factor", dataIndex: "form_factor" },
                { title: "Si Stepping (top)", dataIndex: "si_stepping" },
                { title: "PCB Rev (top)", dataIndex: "pcb_revision" },
                {
                  title: "Builds",
                  dataIndex: "builds",
                  align: "right",
                  width: 90,
                },
                {
                  title: "Boards",
                  dataIndex: "boards",
                  align: "right",
                  width: 110,
                  render: (v) => v.toLocaleString(),
                },
              ]}
            />
          </Card>
        </>
      )}
    </Card>
  );
}

function dominant(arr) {
  if (!arr || arr.length === 0) return "—";
  const sorted = [...arr].sort((a, b) => b.value - a.value);
  const top = sorted[0];
  return arr.length > 1 ? `${top.label} (+${arr.length - 1})` : top.label;
}

function Tag({ count, label }) {
  return (
    <div
      style={{
        background: "rgba(22,119,255,0.08)",
        color: "#1677ff",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 12,
      }}
    >
      <b>{Number(count || 0).toLocaleString()}</b> {label}
    </div>
  );
}

function MiniPie({ title, data }) {
  if (!data || data.length === 0) {
    return (
      <div style={{ textAlign: "center" }}>
        <Text type="secondary" style={{ fontSize: 11 }}>
          {title}
        </Text>
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="—" />
      </div>
    );
  }
  const cfg = {
    data: data.map((d) => ({ type: d.label, value: d.value })),
    angleField: "value",
    colorField: "type",
    radius: 1,
    innerRadius: 0.5,
    height: 120,
    legend: false,
    label: false,
    tooltip: {
      title: (d) => d.type,
      items: [{ channel: "y" }],
    },
  };
  return (
    <div style={{ textAlign: "center" }}>
      <Text type="secondary" style={{ fontSize: 11 }}>
        {title}
      </Text>
      <Pie {...cfg} />
    </div>
  );
}
