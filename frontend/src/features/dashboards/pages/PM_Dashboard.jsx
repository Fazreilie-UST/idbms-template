import { useEffect, useMemo, useState } from "react";
import { Card, Col, Row, Select, Space, Statistic, Table, Tabs, Tag, Typography, Alert } from "antd";
import {
  BookOutlined,
  SolutionOutlined,
  TruckOutlined,
  PauseCircleOutlined,
  PlusCircleOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { fetchBuildPlans } from "@/features/buildplans/services/build_plan_service";
import { fetchBuildRequests } from "@/features/orders/services/build_request_service";
import { fetchShippings } from "@/features/shipments/services/shipping_service";
import { fetchPMFamilies } from "@/features/admin/services/pm_family_service";
import { useAuthStore } from "@/shared/store/useAuthStore";
import BusinessOverview from "@/features/dashboards/components/BusinessOverview";

const { Title } = Typography;

export default function PMDashboard() {
  const navigate = useNavigate();
  const authUser = useAuthStore((s) => s.user);
  const currentUserId = authUser?.id ?? null;
  const [plans, setPlans] = useState({ data: [], total: 0 });
  const [orders, setOrders] = useState({ data: [], total: 0 });
  const [shipments, setShipments] = useState({ data: [], total: 0 });
  const [statusCounts, setStatusCounts] = useState({ New: 0, Hold: 0, Plan: 0, Done: 0 });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [familyOptions, setFamilyOptions] = useState([]);
  const [selectedFamilies, setSelectedFamilies] = useState([]);

  // Load the families the current PM is handling (pm_families assignments).
  useEffect(() => {
    if (currentUserId == null) return;
    let cancelled = false;
    (async () => {
      try {
        const rows = await fetchPMFamilies({ userId: currentUserId });
        if (cancelled) return;
        const opts = (rows || [])
          .map((r) => r.family?.code)
          .filter(Boolean);
        // Dedup while preserving order.
        const uniq = Array.from(new Set(opts));
        setFamilyOptions(uniq);
      } catch {
        if (!cancelled) setFamilyOptions([]);
      }
    })();
    return () => { cancelled = true; };
  }, [currentUserId]);

  const familyParam = useMemo(
    () => (selectedFamilies.length ? selectedFamilies.join(",") : undefined),
    [selectedFamilies],
  );

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      const recencySort = {
        sort_by: "year,work_week",
        sort_order: "desc,desc",
      };
      const bpFamily = familyParam ? { family_code: familyParam } : {};
      const brFamily = familyParam ? { family: familyParam } : {};
      const shipFamily = familyParam ? { family: familyParam } : {};
      try {
        const [bp, statusNew, statusHold, statusPlan, statusDone, ord, ship] = await Promise.all([
          fetchBuildPlans({ page: 1, page_size: 5, my_plans: true, owner_only: true, ...recencySort, ...bpFamily }).catch(() => ({ data: [], pagination: { total: 0 } })),
          fetchBuildPlans({ page: 1, page_size: 1, my_plans: true, owner_only: true, status: "New", ...bpFamily }).catch(() => ({ data: [], pagination: { total: 0 } })),
          fetchBuildPlans({ page: 1, page_size: 1, my_plans: true, owner_only: true, status: "Hold", ...bpFamily }).catch(() => ({ data: [], pagination: { total: 0 } })),
          fetchBuildPlans({ page: 1, page_size: 1, my_plans: true, owner_only: true, status: "Plan", ...bpFamily }).catch(() => ({ data: [], pagination: { total: 0 } })),
          fetchBuildPlans({ page: 1, page_size: 1, my_plans: true, owner_only: true, status: "Done", ...bpFamily }).catch(() => ({ data: [], pagination: { total: 0 } })),
          fetchBuildRequests({ page: 1, page_size: 5, my_plans: true, sort_by: "build_plan_recency", sort_order: "desc", ...brFamily }).catch(() => ({ data: [], total: 0 })),
          fetchShippings({ page: 1, page_size: 5, my_plans: true, sort_by: "build_plan_recency", sort_order: "desc", ...shipFamily }).catch(() => ({ data: [], total: 0 })),
        ]);
        if (cancelled) return;
        setPlans({ data: bp.data || [], total: bp.pagination?.total || 0 });
        setStatusCounts({
          New: statusNew.pagination?.total || 0,
          Hold: statusHold.pagination?.total || 0,
          Plan: statusPlan.pagination?.total || 0,
          Done: statusDone.pagination?.total || 0,
        });
        setOrders(ord);
        setShipments(ship);
      } catch (e) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [familyParam]);

  const goToBuildPlans = (view) =>
    navigate("/pm/build-plans", {
      state: { view, family_code: familyParam || undefined },
    });

  const buildPlanCards = useMemo(() => ([
    { title: "My Build Plans", value: plans.total, icon: <BookOutlined />, onClick: () => goToBuildPlans("my_plans") },
    { title: "New", value: statusCounts.New, icon: <PlusCircleOutlined />, onClick: () => goToBuildPlans("New") },
    { title: "Hold", value: statusCounts.Hold, icon: <PauseCircleOutlined />, onClick: () => goToBuildPlans("Hold") },
    { title: "Plan", value: statusCounts.Plan, icon: <FileTextOutlined />, onClick: () => goToBuildPlans("Plan") },
    { title: "Completed", value: statusCounts.Done, icon: <CheckCircleOutlined />, onClick: () => goToBuildPlans("Done") },
  ]), [plans.total, statusCounts, navigate]);

  const otherCards = useMemo(() => ([
    { title: "Build Requests", value: orders.total, icon: <SolutionOutlined />, onClick: () => navigate("/pm/build-requests") },
    { title: "Shipments", value: shipments.total, icon: <TruckOutlined />, onClick: () => navigate("/pm/shippings") },
  ]), [orders.total, shipments.total, navigate]);

  const myPlansContent = (
    <Space orientation="vertical" size="large" style={{ width: "100%" }}>
      {error && <Alert type="error" showIcon message={error} />}

      <Select
        mode="multiple"
        allowClear
        style={{ width: "100%", maxWidth: 480 }}
        placeholder={
          familyOptions.length
            ? "Family (all)"
            : "No families assigned to you"
        }
        value={selectedFamilies}
        onChange={setSelectedFamilies}
        options={familyOptions.map((f) => ({ label: f, value: f }))}
        disabled={familyOptions.length === 0}
      />

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card title="Build Plans" size="small" styles={{ body: { padding: 12 } }}>
            <Row gutter={[12, 12]}>
              {buildPlanCards.map((c) => (
                <Col xs={12} sm={8} key={c.title}>
                  <Card hoverable onClick={c.onClick} loading={loading} size="small">
                    <Statistic title={c.title} value={c.value} prefix={c.icon} />
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title="Orders & Shipments" size="small" styles={{ body: { padding: 12 } }}>
            <Row gutter={[12, 12]}>
              {otherCards.map((c) => (
                <Col xs={12} key={c.title}>
                  <Card hoverable onClick={c.onClick} loading={loading} size="small">
                    <Statistic title={c.title} value={c.value} prefix={c.icon} />
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="My Recent Build Plans" loading={loading}>
            <Table
              size="small"
              rowKey="build_plan_id"
              pagination={false}
              dataSource={plans.data}
              columns={[
                { title: "#", dataIndex: "build_plan_id", width: 70 },
                { title: "Config", dataIndex: "config_number" },
                { title: "Status", dataIndex: "status", render: (s) => <Tag>{s}</Tag> },
              ]}
              onRow={(r) => ({ onClick: () => navigate(`/pm/build-plans/${r.build_plan_id}`), style: { cursor: "pointer" } })}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Recent Build Requests" loading={loading}>
            <Table
              size="small"
              rowKey="id"
              pagination={false}
              dataSource={orders.data}
              columns={[
                { title: "#", dataIndex: "id", width: 70 },
                { title: "Config", dataIndex: "config_number" },
                { title: "Qty", dataIndex: "quantity", width: 70 },
                { title: "Status", dataIndex: "status", render: (s) => <Tag>{s}</Tag> },
              ]}
              onRow={(r) => ({ onClick: () => navigate(`/pm/build-requests/${r.id}`), style: { cursor: "pointer" } })}
            />
          </Card>
        </Col>
        <Col xs={24}>
          <Card title="Recent Shipments" loading={loading}>
            <Table
              size="small"
              rowKey="id"
              pagination={false}
              dataSource={shipments.data}
              columns={[
                { title: "#", dataIndex: "id", width: 70 },
                { title: "Config", dataIndex: "config_number" },
                { title: "Tracking", dataIndex: "tracking_number" },
                { title: "Status", dataIndex: "status", render: (s) => <Tag>{s}</Tag> },
                { title: "ETA", dataIndex: "eta" },
              ]}
              onRow={(r) => ({ onClick: () => navigate(`/pm/shippings/${r.id}`), style: { cursor: "pointer" } })}
            />
          </Card>
        </Col>
      </Row>
    </Space>
  );

  return (
    <Space orientation="vertical" size="large" style={{ width: "100%" }}>
      <Title level={3} style={{ margin: 0 }}>Program Manager Dashboard</Title>
      <Tabs
        defaultActiveKey="mine"
        items={[
          { key: "mine", label: "My Build Plans", children: myPlansContent },
          {
            key: "business",
            label: "Overview",
            children: <BusinessOverview />,
          },
        ]}
      />
    </Space>
  );
}
