import {
  Row,
  Col,
  Card,
  Statistic,
  Table,
  List,
  Tag,
  Progress,
  Typography,
  Space,
  Button,
} from "antd";
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  DatabaseOutlined,
  UploadOutlined,
  BarChartOutlined,
  ReloadOutlined,
} from "@ant-design/icons";

const { Title, Text } = Typography;

const kpiData = [
  {
    title: "Total Stocks",
    value: 248,
    prefix: <DatabaseOutlined />,
  },
  {
    title: "Financial Records",
    value: 182340,
    prefix: <BarChartOutlined />,
  },
  {
    title: "Data Growth",
    value: 12.8,
    suffix: "%",
    prefix: <ArrowUpOutlined />,
    styles: { color: "#3f8600" },
  },
  {
    title: "Missing Records",
    value: 3.2,
    suffix: "%",
    prefix: <ArrowDownOutlined />,
    styles: { color: "#cf1322" },
  },
];

const stockColumns = [
  {
    title: "Stock Code",
    dataIndex: "stock_code",
    key: "stock_code",
  },
  {
    title: "Stock Name",
    dataIndex: "stock_name",
    key: "stock_name",
  },
  {
    title: "Price",
    dataIndex: "price",
    key: "price",
  },
  {
    title: "Status",
    dataIndex: "status",
    key: "status",
    render: (status) => (
      <Tag color={status === "Healthy" ? "green" : "orange"}>{status}</Tag>
    ),
  },
];

const stockData = [
  {
    key: 1,
    stock_code: "AAPL",
    stock_name: "Apple Inc.",
    price: "176.20",
    status: "Healthy",
  },
  {
    key: 2,
    stock_code: "MSFT",
    stock_name: "Microsoft Corp.",
    price: "421.10",
    status: "Healthy",
  },
  {
    key: 3,
    stock_code: "TSLA",
    stock_name: "Tesla Inc.",
    price: "168.54",
    status: "Warning",
  },
];

const activityData = [
  "Uploaded quarterly financial dataset",
  "Refreshed dim_metric records",
  "Generated preview for custom query builder",
  "Updated stock master entries",
  "Synced statement dimension table",
];

const metricSummary = [
  {
    name: "Revenue",
    percent: 82,
  },
  {
    name: "Net Income",
    percent: 67,
  },
  {
    name: "EPS",
    percent: 54,
  },
  {
    name: "Operating Margin",
    percent: 74,
  },
];

export default function Dashboard() {
  return (
    <Space orientation="vertical" size={24} style={{ width: "100%" }}>
      <div>
        <Title level={2} style={{ marginBottom: 4 }}>
          Dashboard
        </Title>
        <Text type="secondary">
          Overview of stock data, financial records, and system activity.
        </Text>
      </div>

      <Row gutter={[16, 16]}>
        {kpiData.map((item) => (
          <Col xs={24} sm={12} lg={6} key={item.title}>
            <Card style={{ borderRadius: 12 }}>
              <Statistic
                title={item.title}
                value={item.value}
                prefix={item.prefix}
                suffix={item.suffix}
                styles={item.styles}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card
            title="Recent Stocks Snapshot"
            extra={<Button type="link">View all</Button>}
            style={{ borderRadius: 12 }}
          >
            <Table
              columns={stockColumns}
              dataSource={stockData}
              pagination={false}
              scroll={{ x: "max-content" }}
            />
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          <Card title="Quick Actions" style={{ borderRadius: 12 }}>
            <Space orientation="vertical" style={{ width: "100%" }}>
              <Button type="primary" icon={<UploadOutlined />} block>
                Upload Data
              </Button>
              <Button icon={<BarChartOutlined />} block>
                Open Query Builder
              </Button>
              <Button icon={<ReloadOutlined />} block>
                Refresh Dashboard
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="Recent Activity" style={{ borderRadius: 12 }}>
            <List
              dataSource={activityData}
              renderItem={(item) => <List.Item>{item}</List.Item>}
            />
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="Metric Coverage" style={{ borderRadius: 12 }}>
            <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
              {metricSummary.map((item) => (
                <div key={item.name}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      marginBottom: 6,
                    }}
                  >
                    <Text>{item.name}</Text>
                    <Text>{item.percent}%</Text>
                  </div>
                  <Progress percent={item.percent} showInfo={false} />
                </div>
              ))}
            </Space>
          </Card>
        </Col>
      </Row>
    </Space>
  );
}