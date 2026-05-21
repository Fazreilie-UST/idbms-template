import { useEffect, useState } from "react";
import { Alert, Card, Col, Row, Space, Statistic, Table, Tag, Typography } from "antd";
import { SolutionOutlined, FileSearchOutlined, TruckOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { fetchBuildRequests } from "@/features/orders/services/build_request_service";
import { fetchShippings } from "@/features/shipments/services/shipping_service";

const { Title } = Typography;

export default function RequestorDashboard() {
  const navigate = useNavigate();
  const [myOrders, setMyOrders] = useState({ data: [], total: 0 });
  const [pending, setPending] = useState({ data: [], total: 0 });
  const [shipments, setShipments] = useState({ data: [], total: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const [my, pend, ship] = await Promise.all([
          fetchBuildRequests({ page: 1, page_size: 5, my_orders: true }).catch(() => ({ data: [], total: 0 })),
          fetchBuildRequests({ page: 1, page_size: 1, my_orders: true, status: "Submitted" }).catch(() => ({ data: [], total: 0 })),
          fetchShippings({ page: 1, page_size: 5 }).catch(() => ({ data: [], total: 0 })),
        ]);
        if (cancelled) return;
        setMyOrders(my);
        setPending(pend);
        setShipments(ship);
      } catch (e) {
        if (!cancelled) setError(e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  const cards = [
    { title: "My Orders", value: myOrders.total, icon: <SolutionOutlined />, onClick: () => navigate("/requestor/build-requests") },
    { title: "Awaiting Review", value: pending.total, icon: <FileSearchOutlined />, onClick: () => navigate("/requestor/build-requests") },
    { title: "Shipments", value: shipments.total, icon: <TruckOutlined />, onClick: () => navigate("/shipment-tracker") },
  ];

  return (
    <Space orientation="vertical" size="large" style={{ width: "100%" }}>
      <Title level={3} style={{ margin: 0 }}>Requestor Dashboard</Title>

      {error && <Alert type="error" showIcon message={error} />}

      <Row gutter={[16, 16]}>
        {cards.map((c) => (
          <Col xs={12} md={8} key={c.title}>
            <Card hoverable loading={loading} onClick={c.onClick}>
              <Statistic title={c.title} value={c.value} prefix={c.icon} />
            </Card>
          </Col>
        ))}
      </Row>

      <Card title="My Recent Build Requests" loading={loading}>
        <Table
          size="small"
          rowKey="id"
          pagination={false}
          dataSource={myOrders.data}
          columns={[
            { title: "#", dataIndex: "id", width: 70 },
            { title: "Config", dataIndex: "config_number" },
            { title: "Qty", dataIndex: "quantity", width: 70 },
            { title: "Rev", dataIndex: "revision", width: 70, render: (v) => `rev${v ?? 1}` },
            { title: "Status", dataIndex: "status", render: (s) => <Tag>{s}</Tag> },
          ]}
          onRow={(r) => ({ onClick: () => navigate(`/requestor/build-requests/${r.id}`), style: { cursor: "pointer" } })}
        />
      </Card>
    </Space>
  );
}
