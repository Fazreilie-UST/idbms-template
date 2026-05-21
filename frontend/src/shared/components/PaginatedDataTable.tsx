import { Card, Table, Typography } from "antd";
import type { TableProps } from "antd";

const { Title, Text } = Typography;

interface PaginatedDataTableProps<TRow> {
  title: string;
  subtitle?: string;
  columns: NonNullable<TableProps<TRow>["columns"]>;
  data: TRow[];
  total: number;
  loading?: boolean;
  page: number;
  pageSize: number;
  onChange?: TableProps<TRow>["onChange"];
  rowKey?: TableProps<TRow>["rowKey"];
}

export default function PaginatedDataTable<TRow extends object = Record<string, unknown>>({
  title,
  subtitle,
  columns,
  data,
  total,
  loading,
  page,
  pageSize,
  onChange,
  rowKey = "id" as TableProps<TRow>["rowKey"],
}: PaginatedDataTableProps<TRow>) {
  return (
    <Card style={{ borderRadius: 12 }}>
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ marginBottom: 4 }}>
          {title}
        </Title>
        {subtitle && <Text type="secondary">{subtitle}</Text>}
      </div>

      <Table<TRow>
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
