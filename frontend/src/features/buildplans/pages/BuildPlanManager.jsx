import { useState } from "react";
import { useLocation } from "react-router-dom";
import { Button, Card, Segmented, Typography, message } from "antd";
import {
  UserOutlined,
  FileTextOutlined,
  PauseCircleOutlined,
  CheckCircleOutlined,
  PlusCircleOutlined,
  UsergroupAddOutlined,
} from "@ant-design/icons";
import BuildPlanTable from "@/features/buildplans/components/BuildPlanTable";
import GrantAccessModal from "@/features/buildplans/components/GrantAccessModal";
import { useBuildPlanTable } from "@/features/buildplans/hooks/useBuildPlanTable";

const { Title } = Typography;

const VIEW_OPTIONS = [
  { label: "Managed by me", value: "my_plans", icon: <UserOutlined /> },
  { label: "New", value: "New", icon: <PlusCircleOutlined /> },
  { label: "Hold", value: "Hold", icon: <PauseCircleOutlined /> },
  { label: "Plan", value: "Plan", icon: <FileTextOutlined /> },
  { label: "Completed", value: "Done", icon: <CheckCircleOutlined /> },
];

export default function BuildPlanManager() {
  const location = useLocation();
  const initialView = VIEW_OPTIONS.some((o) => o.value === location.state?.view)
    ? location.state.view
    : "my_plans";
  const initialFamily =
    typeof location.state?.family_code === "string"
      ? location.state.family_code
      : "";
  const [activeView, setActiveView] = useState(initialView);
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [grantModalOpen, setGrantModalOpen] = useState(false);

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
  } = useBuildPlanTable({
    my_plans: true,
    status: initialView === "my_plans" ? "" : initialView,
    family_code: initialFamily,
  });

  function handleViewChange(value) {
    setActiveView(value);
    if (value === "my_plans") {
      updateFilters({ my_plans: true, status: "" });
    } else {
      updateFilters({ my_plans: true, status: value });
    }
  }

  const selectionCount = selectedRowKeys.length;

  return (
    <Card>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
        }}
      >
        <Title level={3} style={{ margin: 0 }}>
          Build Plans
        </Title>

        <Segmented
          options={VIEW_OPTIONS}
          value={activeView}
          onChange={handleViewChange}
        />
      </div>

      <BuildPlanTable
        rows={rows}
        loading={loading}
        pagination={pagination}
        filters={filters}
        filterOptions={filterOptions}
        updateFilters={updateFilters}
        resetAllFilters={() => {
          setActiveView("my_plans");
          setSelectedRowKeys([]);
          resetAllFilters();
        }}
        handleTableChange={handleTableChange}
        reload={loadData}
        selectable
        selectedRowKeys={selectedRowKeys}
        onSelectionChange={setSelectedRowKeys}
        hideStatusColumn={activeView !== "my_plans"}
        toolbarExtra={
          <Button
            type="primary"
            icon={<UsergroupAddOutlined />}
            disabled={selectionCount === 0}
            onClick={() => setGrantModalOpen(true)}
          >
            Grant Access{selectionCount ? ` (${selectionCount})` : ""}
          </Button>
        }
      />

      <GrantAccessModal
        open={grantModalOpen}
        onClose={() => setGrantModalOpen(false)}
        buildPlanIds={selectedRowKeys}
        onGranted={(result) => {
          const parts = [];
          if (result.granted) parts.push(`${result.granted} granted`);
          if (result.upgraded) parts.push(`${result.upgraded} upgraded`);
          if (result.unchanged) parts.push(`${result.unchanged} unchanged`);
          message.success(
            `Access updated${parts.length ? `: ${parts.join(", ")}` : ""}.`,
          );
          setSelectedRowKeys([]);
          loadData();
        }}
      />
    </Card>
  );
}

