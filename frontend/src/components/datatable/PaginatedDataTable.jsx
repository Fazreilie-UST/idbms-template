import { Card, Table, Typography } from "antd";

const { Title, Text } = Typography;

export default function PaginatedDataTable({
  title,
  subtitle,
  columns,
  data,
  total,
  loading,
  page,
  pageSize,
  onChange,
  rowKey = "id",
}) {
  return (
    <Card style={{ borderRadius: 12 }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ marginBottom: 4 }}>
          {title}
        </Title>
        {subtitle && <Text type="secondary">{subtitle}</Text>}
      </div>

      <Table
        rowKey={rowKey}
        columns={columns}
        dataSource={data}
        loading={loading}
        onChange={onChange}
        pagination={{
          current: page,
          pageSize,
          total,
          showSizeChanger: true,
          pageSizeOptions: ["10", "20", "50", "100"],
          showTotal: (value) => `Total ${value} records`,
        }}
        scroll={{ x: "max-content" }}
      />
    </Card>
  );
}