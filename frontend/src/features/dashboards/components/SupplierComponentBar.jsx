import { useEffect, useMemo, useState } from "react";
import { Card, Col, Divider, Empty, Row, Select, Skeleton } from "antd";
import ChartInfoTooltip from "./ChartInfoTooltip";
import { Column } from "@ant-design/charts";
import {
  fetchLookups,
  fetchSupplierComponent,
} from "../services/dashboard_service";
import { useDashboardFilters } from "../state/DashboardFiltersContext";
import SupplierComponentDetailTable from "./SupplierComponentDetailTable";
import PcbSupplierCountBar from "./PcbSupplierCountBar";

/**
 * Two bar charts side-by-side — for the selected component/slot, shows
 * "Builds by Supplier" and "Boards by Supplier".
 *
 * Dropdown lists every <component>_<slot> combination present in the data
 * (slot may be empty when a component has no slots).
 */

function makeKey(componentName, slotCode) {
  return `${componentName}\u0000${slotCode ?? ""}`;
}

function makeLabel(componentName, slotCode) {
  return slotCode ? `${componentName}_${slotCode}` : componentName;
}

export default function SupplierComponentBar() {
  const { filters } = useDashboardFilters();
  const [options, setOptions] = useState([]); // [{key, label, component, slot}]
  const [selectedKey, setSelectedKey] = useState(null);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  // Fetch dropdown options once on mount.
  useEffect(() => {
    fetchLookups()
      .then((d) => {
        const pairs = d?.component_slots ?? [];
        const opts = pairs.map((p) => ({
          key: makeKey(p.component_name, p.slot_code),
          label: makeLabel(p.component_name, p.slot_code),
          component: p.component_name,
          slot: p.slot_code ?? null,
        }));
        setOptions(opts);
        if (opts.length > 0) {
          const preferred =
            opts.find((o) => o.component === "Crystal") ?? opts[0];
          setSelectedKey(preferred.key);
        }
      })
      .catch(() => {});
  }, []);

  const selected = useMemo(
    () => options.find((o) => o.key === selectedKey) || null,
    [options, selectedKey],
  );

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    setLoading(true);
    fetchSupplierComponent(selected.component, "boards", selected.slot, filters)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setData(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [selected, filters]);

  // Aggregate by supplier.
  const aggregated = useMemo(() => {
    if (!data?.rows) return [];
    const map = new Map();
    for (const r of data.rows) {
      const key = r.supplier || "Unknown";
      const cur = map.get(key) || { supplier: key, builds: 0, boards: 0 };
      cur.builds += Number(r.builds) || 0;
      cur.boards += Number(r.boards) || 0;
      map.set(key, cur);
    }
    return Array.from(map.values());
  }, [data]);

  const buildsData = useMemo(
    () =>
      [...aggregated]
        .sort((a, b) => b.builds - a.builds)
        .map((r) => ({ supplier: r.supplier, value: r.builds })),
    [aggregated],
  );

  const boardsData = useMemo(
    () =>
      [...aggregated]
        .sort((a, b) => b.boards - a.boards)
        .map((r) => ({ supplier: r.supplier, value: r.boards })),
    [aggregated],
  );

  const isEmpty = aggregated.length === 0;
  const buildsEmpty = buildsData.every((d) => d.value === 0);
  const boardsEmpty = boardsData.every((d) => d.value === 0);

  const title = (
    <Row align="middle" gutter={8} wrap={false}>
      <Col style={{ whiteSpace: "nowrap" }}>Component :</Col>
      <Col flex="auto">
        <Select
          size="small"
          value={selectedKey}
          onChange={setSelectedKey}
          style={{ minWidth: 180, width: "100%", maxWidth: 280 }}
          options={options.map((o) => ({ label: o.label, value: o.key }))}
          loading={options.length === 0}
          showSearch
          filterOption={(input, option) =>
            option.label.toLowerCase().includes(input.toLowerCase())
          }
        />
      </Col>
    </Row>
  );

  const baseConfig = {
    xField: "supplier",
    yField: "value",
    height: 280,
    label: {
      position: "top",
      formatter: (d) => {
        const v = Number(d?.value ?? d);
        if (!Number.isFinite(v) || v === 0) return "";
        return Math.round(v).toLocaleString();
      },
      style: { fontSize: 11 },
    },
    axis: { x: { labelAutoRotate: true, labelAutoHide: false } },
    style: { maxWidth: 48 },
  };

  return (
    <Card
      title={
        <>
          {title}
          <ChartInfoTooltip title="Counts of builds and boards grouped by supplier for the selected component." />
        </>
      }
      size="small"
    >
      {loading ? (
        <Skeleton active paragraph={{ rows: 6 }} />
      ) : !selected || isEmpty ? (
        <Empty description={selected ? "No data" : "Select a component"} />
      ) : (
        <>
          <Row gutter={[12, 12]}>
            <Col xs={24} lg={12}>
              <Card type="inner" size="small" title="Builds by Supplier">
                {buildsEmpty ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No data" />
                ) : (
                  <Column
                    {...baseConfig}
                    data={buildsData}
                    colorField="supplier"
                    scale={{ color: { palette: "category10" } }}
                    legend={false}
                    tooltip={{
                      title: (d) => d.supplier,
                      items: [
                        {
                          name: "Builds",
                          field: "value",
                          valueFormatter: (v) => Number(v).toLocaleString(),
                        },
                      ],
                    }}
                  />
                )}
              </Card>
            </Col>
            <Col xs={24} lg={12}>
              <Card type="inner" size="small" title="Boards by Supplier">
                {boardsEmpty ? (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="No data" />
                ) : (
                  <Column
                    {...baseConfig}
                    data={boardsData}
                    colorField="supplier"
                    scale={{ color: { palette: "category10" } }}
                    legend={false}
                    tooltip={{
                      title: (d) => d.supplier,
                      items: [
                        {
                          name: "Boards",
                          field: "value",
                          valueFormatter: (v) =>
                            Math.round(Number(v)).toLocaleString(),
                        },
                      ],
                    }}
                  />
                )}
              </Card>
            </Col>
          </Row>
          <Divider style={{ margin: "16px 0 12px" }} titlePlacement="left">
            Detail by attributes
          </Divider>
          <SupplierComponentDetailTable
            componentName={selected.component}
            slotCode={selected.slot}
          />
          <div style={{ marginTop: 16 }}>
            <PcbSupplierCountBar
              componentName={selected.component}
              slotCode={selected.slot}
            />
          </div>
        </>
      )}
    </Card>
  );
}
