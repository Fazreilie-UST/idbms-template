import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  Alert,
  Breadcrumb,
  Button,
  Card,
  Descriptions,
  Space,
  Spin,
  Tag,
  Typography,
} from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { fetchShippingById } from "@/features/shipments/services/shipping_service";

const { Title } = Typography;

const STATUS_COLORS = {
  Scheduled: "processing",
  ShippedOut: "warning",
  Delivered: "success",
  Completed: "success",
};

export default function ShippingView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const d = await fetchShippingById(id);
        if (!cancelled) setData(d);
      } catch (e) {
        if (!cancelled) setError(e.message || "Failed to load");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, [id]);

  if (loading) return <div style={{ textAlign: "center", padding: "80px 0" }}><Spin size="large" /></div>;
  if (error) return (
    <Alert type="error" message="Failed to load shipment" description={error} showIcon
      action={<Button size="small" onClick={() => navigate(-1)}>Go Back</Button>} />
  );

  return (
    <>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>Back</Button>
        <Breadcrumb items={[{ title: "Shipments" }, { title: `#${data?.id}` }]} />
      </Space>

      <Title level={4} style={{ marginBottom: 24 }}>
        Shipment #{data?.id}
        <Tag style={{ marginLeft: 12, verticalAlign: "middle" }} color={STATUS_COLORS[data?.status] || "default"}>
          {data?.status}
        </Tag>
      </Title>

      <Card>
        <Descriptions bordered size="small" column={{ xs: 1, sm: 2, md: 3 }}>
          <Descriptions.Item label="Config Number">{data?.config_number || "\u2014"}</Descriptions.Item>
          <Descriptions.Item label="Tracking #">{data?.tracking_number || "\u2014"}</Descriptions.Item>
          <Descriptions.Item label="Forwarder">{data?.forwarder || "\u2014"}</Descriptions.Item>
          <Descriptions.Item label="Quantity">{data?.quantity ?? "\u2014"}</Descriptions.Item>
          <Descriptions.Item label="Ship Date">{data?.ship_date || "\u2014"}</Descriptions.Item>
          <Descriptions.Item label="ETA">{data?.eta || "\u2014"}</Descriptions.Item>
          <Descriptions.Item label="Delivery Date">{data?.delivery_date || "\u2014"}</Descriptions.Item>
          <Descriptions.Item label="Handler">{data?.recipient_user?.full_name || "\u2014"}</Descriptions.Item>
          <Descriptions.Item label="Recipients">
            {(data?.recipients || []).length
              ? (data.recipients || []).map((u) => u.full_name).filter(Boolean).join(", ")
              : "\u2014"}
          </Descriptions.Item>
          <Descriptions.Item label="Comments" span={3}>{data?.comments || "\u2014"}</Descriptions.Item>
        </Descriptions>
      </Card>
    </>
  );
}
