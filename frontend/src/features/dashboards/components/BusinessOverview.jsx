import { Col, Row, Space } from "antd";
import FilterBar from "./FilterBar";
import KpiStrip from "./KpiStrip";
import FamilyDonutGrid from "./FamilyDonutGrid";
import FamilyAttributePieGrid from "./FamilyAttributePieGrid";
import SupportActivityStackedBar from "./SupportActivityStackedBar";
import SiliconSteppingPie from "./SiliconSteppingPie";
import RequiredQuantityTopBar from "./RequiredQuantityTopBar";
import MilestoneTimeline from "./MilestoneTimeline";
import SupplierComponentBar from "./SupplierComponentBar";
import { DashboardFiltersProvider } from "../state/DashboardFiltersContext";

/**
 * Business Overview page — org-wide reporting with Power-BI-style
 * cross-filtering. Every widget reads the shared filter state; clicking a
 * chart segment toggles a filter and all widgets refetch.
 */
export default function BusinessOverview() {
  return (
    <DashboardFiltersProvider>
      <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
        <FilterBar />
        <KpiStrip />

        <Row gutter={[12, 12]}>
          <Col xs={24}>
            <FamilyDonutGrid />
          </Col>
          <Col xs={24}>
            <FamilyAttributePieGrid />
          </Col>
          <Col xs={24} lg={16}>
            <SupportActivityStackedBar />
          </Col>
          <Col xs={24} lg={8}>
            <SiliconSteppingPie />
          </Col>

          <Col xs={24} lg={14}>
            <RequiredQuantityTopBar />
          </Col>
          <Col xs={24} lg={10}>
            <MilestoneTimeline />
          </Col>

          <Col xs={24}>
            <SupplierComponentBar />
          </Col>
        </Row>
      </Space>
    </DashboardFiltersProvider>
  );
}
