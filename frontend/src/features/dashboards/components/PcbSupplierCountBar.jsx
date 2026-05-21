import { useEffect, useMemo, useState } from "react";
import { Card, Col, Empty, Row, Skeleton } from "antd";
import { Column } from "@ant-design/charts";
import { fetchSupplierComponentByPcbSupplier } from "../services/dashboard_service";
import { useDashboardFilters } from "../state/DashboardFiltersContext";

/**
 * Two bar charts side-by-side showing, for the selected component/slot,
 * the count of builds and boards grouped by PCB Supplier.
 *
 * "PCB Supplier" is the supplier of the build plan's `PCB` BuildPlanComponent.
 */
export default function PcbSupplierCountBar({ componentName, slotCode }) {
  const { filters } = useDashboardFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!componentName) return;
    let cancelled = false;
    setLoading(true);
    fetchSupplierComponentByPcbSupplier(componentName, slotCode ?? null, filters)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setData(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [componentName, slotCode, filters]);

  const rows = data?.rows ?? [];

  const buildsData = useMemo(
    () =>
      [...rows]
        .sort((a, b) => (b.builds || 0) - (a.builds || 0))
        .map((r) => ({ supplier: r.pcb_supplier || "Unknown", value: r.builds || 0 })),
    [rows],
  );

  const boardsData = useMemo(
    () =>
      [...rows]
        .sort((a, b) => (b.boards || 0) - (a.boards || 0))
        .map((r) => ({ supplier: r.pcb_supplier || "Unknown", value: r.boards || 0 })),
    [rows],
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

  const componentLabel = slotCode ? `${componentName}_${slotCode}` : componentName;
  const isEmpty = rows.length === 0;
  const buildsEmpty = buildsData.every((d) => d.value === 0);
  const boardsEmpty = boardsData.every((d) => d.value === 0);

  if (loading) return <Skeleton active paragraph={{ rows: 6 }} />;
  if (!componentName || isEmpty) {
    return (
      <Empty
        image={Empty.PRESENTED_IMAGE_SIMPLE}
        description={componentName ? "No data" : "Select a component"}
      />
    );
  }

  return (
    <Row gutter={[12, 12]}>
      <Col xs={24} lg={12}>
        <Card
          type="inner"
          size="small"
          title={`Count of ${componentLabel} (builds) by PCB Supplier`}
        >
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
        <Card
          type="inner"
          size="small"
          title={`Count of ${componentLabel} (boards) by PCB Supplier`}
        >
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
  );
}
