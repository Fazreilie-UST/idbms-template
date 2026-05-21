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
  Timeline,
  Typography,
} from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import {
  fetchBuildRequestById,
  fetchBuildRequestRevisions,
} from "@/features/orders/services/build_request_service";

const { Title, Text } = Typography;

const STATUS_COLORS = {
  Draft: "default",
  Submitted: "processing",
  "Under Review": "warning",
  Approved: "success",
  Planned: "blue",
  Locked: "purple",
  Cancelled: "error",
  Rejected: "error",
  Completed: "success",
};

function statusTag(status) {
  if (!status) return "\u2014";
  return <Tag color={STATUS_COLORS[status] || "default"}>{status}</Tag>;
}

export default function BuildRequestView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [revisions, setRevisions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [d, revs] = await Promise.all([
          fetchBuildRequestById(id),
          fetchBuildRequestRevisions(id).catch(() => []),
        ]);
        if (cancelled) return;
        setData(d);
        setRevisions(revs || []);
      } catch (e) {
        if (!cancelled) setError(e.message || "Failed to load");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "80px 0" }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        type="error"
        message="Failed to load build request"
        description={error}
        showIcon
        action={
          <Button size="small" onClick={() => navigate(-1)}>
            Go Back
          </Button>
        }
      />
    );
  }

  const sortedRevisions = [...(revisions || [])].sort(
    (a, b) => (b.revision || 0) - (a.revision || 0),
  );

  return (
    <>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
          Back
        </Button>
        <Breadcrumb
          items={[
            { title: "Build Requests" },
            { title: `#${data?.id}` },
          ]}
        />
      </Space>

      <Title level={4} style={{ marginBottom: 24 }}>
        Build Request #{data?.id}
        <span style={{ marginLeft: 12, verticalAlign: "middle" }}>
          {statusTag(data?.status)}
        </span>
        <Tag style={{ marginLeft: 8 }}>rev{data?.revision ?? 1}</Tag>
      </Title>

      <Card style={{ marginBottom: 24 }} title="Details">
        <Descriptions bordered size="small" column={{ xs: 1, sm: 2, md: 3 }}>
          <Descriptions.Item label="Config Number">
            {data?.config_number || "\u2014"}
          </Descriptions.Item>
          <Descriptions.Item label="Family">{data?.family_code || "\u2014"}</Descriptions.Item>
          <Descriptions.Item label="Form Factor">{data?.form_factor || "\u2014"}</Descriptions.Item>
          <Descriptions.Item label="Quantity">{data?.quantity}</Descriptions.Item>
          <Descriptions.Item label="Revision">rev{data?.revision ?? 1}</Descriptions.Item>
          <Descriptions.Item label="Status">{statusTag(data?.status)}</Descriptions.Item>
          <Descriptions.Item label="Requestor">
            {data?.requestor?.full_name || data?.requestor?.email || `#${data?.requestor_id}`}
          </Descriptions.Item>
          <Descriptions.Item label="Previous Revision">
            {data?.previous_build_request_id ? (
              <a onClick={() => navigate(`../${data.previous_build_request_id}`)}>
                #{data.previous_build_request_id}
              </a>
            ) : (
              "\u2014"
            )}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title={`Revision History (${sortedRevisions.length})`}>
        {sortedRevisions.length === 0 ? (
          <Text type="secondary">No revision history.</Text>
        ) : (
          <Timeline
            items={sortedRevisions.map((r) => ({
              color: r.id === Number(id) ? "blue" : "gray",
              children: (
                <div>
                  <Space>
                    <Text strong>rev{r.revision}</Text>
                    {statusTag(r.status)}
                    <Text>Qty: {r.quantity}</Text>
                    {r.id !== Number(id) && (
                      <a onClick={() => navigate(`../${r.id}`)}>View #{r.id}</a>
                    )}
                  </Space>
                  <div>
                    <Text type="secondary">
                      Requestor: {r.requestor?.full_name || `#${r.requestor?.id || ""}`}
                    </Text>
                  </div>
                </div>
              ),
            }))}
          />
        )}
      </Card>
    </>
  );
}
