import { useEffect, useState } from "react";
import { Card, Col, Row, Select, Space, Tag, Typography, Button } from "antd";
import { fetchLookups } from "../services/dashboard_service";
import { useDashboardFilters } from "../state/DashboardFiltersContext";

const { Text } = Typography;

/**
 * Sticky global filter bar for the Business Overview dashboard.
 * - Year, Family, SKU, Support Activity, Status, Si Stepping selectors.
 * - Active filters render as removable chips below the bar.
 */
export default function FilterBar() {
  const { filters, setYear, setMulti, chips, removeChip, clearAll } =
    useDashboardFilters();
  const [lookups, setLookups] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetchLookups()
      .then((d) => !cancelled && setLookups(d))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const dedupeOptions = (opts) => {
    const seen = new Set();
    const out = [];
    for (const o of opts) {
      if (o.value == null || o.value === "") continue;
      const key = String(o.value);
      if (seen.has(key)) continue;
      seen.add(key);
      out.push(o);
    }
    return out;
  };

  const yearOptions = dedupeOptions(
    lookups?.years?.map((y) => ({ value: y, label: String(y) })) || [],
  );
  const familyOptions = dedupeOptions(
    lookups?.families?.map((f) => {
      // Backend filters by Family.code; show the code only.
      const code = f.label.split(" - ")[0];
      return { value: code, label: code };
    }) || [],
  );
  const formFactorOptions = dedupeOptions(
    lookups?.form_factors?.map((s) => {
      // Backend returns the bare FormFactor.name as the label.
      const name = (s.label ?? "").trim();
      return { value: name, label: name };
    }) || [],
  );
  const statusOptions = dedupeOptions(
    lookups?.statuses?.map((s) => ({ value: s, label: s })) || [],
  );

  return (
    <Card
      size="small"
      styles={{ body: { padding: 12 } }}
      style={{ position: "sticky", top: 0, zIndex: 10 }}
    >
      <Row gutter={[8, 8]} align="middle">
        <Col xs={24} md={6}>
          <Select
            allowClear
            placeholder="Year"
            value={filters.year ?? undefined}
            onChange={(v) => setYear(v ?? null)}
            options={yearOptions}
            style={{ width: "100%" }}
          />
        </Col>
        <Col xs={24} md={6}>
          <Select
            mode="multiple"
            allowClear
            maxTagCount="responsive"
            placeholder="Family"
            value={filters.familyCodes}
            onChange={(v) => setMulti("familyCodes", v)}
            options={familyOptions}
            style={{ width: "100%" }}
          />
        </Col>
        <Col xs={24} md={6}>
          <Select
            mode="multiple"
            allowClear
            showSearch
            maxTagCount="responsive"
            placeholder="Form Factor"
            value={filters.formFactors}
            onChange={(v) => setMulti("formFactors", v)}
            options={formFactorOptions}
            optionFilterProp="label"
            style={{ width: "100%" }}
          />
        </Col>
        <Col xs={24} md={6}>
          <Select
            mode="multiple"
            allowClear
            maxTagCount="responsive"
            placeholder="Status"
            value={filters.statuses}
            onChange={(v) => setMulti("statuses", v)}
            options={statusOptions}
            style={{ width: "100%" }}
          />
        </Col>
      </Row>

      {chips.length > 0 && (
        <Row style={{ marginTop: 8 }}>
          <Col span={24}>
            <Space size={[4, 4]} wrap>
              <Text type="secondary">Active filters:</Text>
              {chips.map((c) => (
                <Tag
                  key={`${c.key}:${c.value}`}
                  closable
                  onClose={(e) => {
                    e.preventDefault();
                    removeChip(c.key, c.value);
                  }}
                  color="processing"
                >
                  {c.label}
                </Tag>
              ))}
              <Button size="small" type="link" onClick={clearAll}>
                Clear all
              </Button>
            </Space>
          </Col>
        </Row>
      )}
    </Card>
  );
}
