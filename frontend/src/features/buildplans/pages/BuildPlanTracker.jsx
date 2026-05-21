import { Card, Typography } from "antd";
import BuildPlanTable from "@/features/buildplans/components/BuildPlanTable";
import { useBuildPlanTable } from "@/features/buildplans/hooks/useBuildPlanTable";

const { Title } = Typography;

export default function BuildPlanTracker() {
  const {
    rows,
    loading,
    pagination,
    filters,
    filterOptions,
    updateFilters,
    resetAllFilters,
    handleTableChange,
    loadData,
  } = useBuildPlanTable();

  return (
    <Card>
      <Title level={3}>Build Plan Tracker</Title>

      <BuildPlanTable
        rows={rows}
        loading={loading}
        pagination={pagination}
        filters={filters}
        filterOptions={filterOptions}
        updateFilters={updateFilters}
        resetAllFilters={resetAllFilters}
        handleTableChange={handleTableChange}
        reload={loadData}
      />
    </Card>
  );
}