import { useEffect, useMemo, useState } from "react";
import {
  Card,
  Select,
  Button,
  Space,
  Typography,
  Row,
  Col,
  Table,
  message,
  Empty,
  Tag,
} from "antd";
import {
  SearchOutlined,
  ClearOutlined,
  TableOutlined,
} from "@ant-design/icons";
import {
  fetchStockMaster,
  fetchStatements,
  previewStockStatementExplorer,
} from "../../services/stock_service";
import { useAuthStore } from "../../store/useAuthStore";
import ExportDropdown from "../../components/dropdown/ExportDropdown";
import {
  buildMetricTreeRows,
  flattenTreeRowsForExport,
  formatFinancialValue,
} from "../../utils/stockExplorerTransform";
import {
  exportStockExplorerJson,
  exportStockExplorerCsv,
  exportStockExplorerPdf,
} from "../../utils/stockExplorerExport";

const { Title, Text } = Typography;

export default function StockExplorerPage() {
  const token = useAuthStore((state) => state.token);

  const [loadingFilters, setLoadingFilters] = useState(false);
  const [loadingPreview, setLoadingPreview] = useState(false);

  const [stockOptions, setStockOptions] = useState([]);
  const [statementOptions, setStatementOptions] = useState([]);

  const [selectedStockId, setSelectedStockId] = useState(null);
  const [selectedStatementId, setSelectedStatementId] = useState(null);

  const [summary, setSummary] = useState(null);
  const [tableRows, setTableRows] = useState([]);
  const [dateColumns, setDateColumns] = useState([]);

  useEffect(() => {
    const loadFilters = async () => {
      try {
        setLoadingFilters(true);

        const [stocksRes, statementsRes] = await Promise.all([
          fetchStockMaster(1, 500, token),
          fetchStatements(1, 500, token),
        ]);

        setStockOptions(
          (stocksRes.items || []).map((stock) => ({
            label: `${stock.stock_code} - ${stock.stock_name || "-"}`,
            value: stock.stock_id,
          }))
        );

        setStatementOptions(
          (statementsRes.items || []).map((statement) => ({
            label: statement.statement_name,
            value: statement.statement_id,
          }))
        );
      } catch (error) {
        message.error(error.message || "Failed to load filters");
      } finally {
        setLoadingFilters(false);
      }
    };

    loadFilters();
  }, [token]);

  const runPreview = async () => {
    if (!selectedStockId) {
      message.warning("Please select a stock.");
      return;
    }

    if (!selectedStatementId) {
      message.warning("Please select a statement.");
      return;
    }

    try {
      setLoadingPreview(true);

      const res = await previewStockStatementExplorer(
        {
          stock_id: selectedStockId,
          statement_id: selectedStatementId,
        },
        token
      );

      setSummary(res.summary || null);

      const { rows, dates } = buildMetricTreeRows(res.rows || []);
      setTableRows(rows);
      setDateColumns(dates);

      if (!res.rows || res.rows.length === 0) {
        message.info("No rows returned for the selected stock and statement.");
      }
    } catch (error) {
      console.error("Explorer preview error:", error);
      message.error(error.message || "Failed to preview explorer data");
      setSummary(null);
      setTableRows([]);
      setDateColumns([]);
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleReset = () => {
    setSelectedStockId(null);
    setSelectedStatementId(null);
    setSummary(null);
    setTableRows([]);
    setDateColumns([]);
  };

  const tableColumns = useMemo(() => {
    return [
      {
        title: "Metric",
        dataIndex: "metric_name",
        key: "metric_name",
        fixed: "left",
        width: 360,
        render: (_, record) => {
          const isParent = !record.parent_metric_id;

          return (
            <Space orientation="vertical" size={0}>
              <Text strong={isParent}>{record.metric_name || "-"}</Text>
            </Space>
          );
        },
      },
      ...dateColumns.map((dateKey) => ({
        title: dateKey,
        dataIndex: dateKey,
        key: dateKey,
        align: "right",
        width: 140,
        render: (value) => <Text>{formatFinancialValue(value)}</Text>,
      })),
    ];
  }, [dateColumns]);

  const exportRows = useMemo(() => {
    return flattenTreeRowsForExport(tableRows, dateColumns);
  }, [tableRows, dateColumns]);

  const canExport = exportRows.length > 0;

  return (
    <Space orientation="vertical" size={16} style={{ width: "100%" }}>
      <div>
        <Title level={2} style={{ marginBottom: 4 }}>
          Stock Statement Explorer
        </Title>
        <Text type="secondary">
          Select a stock and statement to view financial metrics in a
          collapsible hierarchy grouped by reporting date.
        </Text>
      </div>

      <Card loading={loadingFilters} style={{ borderRadius: 12 }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} md={12}>
            <Space orientation="vertical" style={{ width: "100%" }}>
              <Text strong>Stock</Text>
              <Select
                allowClear
                showSearch
                placeholder="Select stock"
                value={selectedStockId}
                onChange={setSelectedStockId}
                options={stockOptions}
                optionFilterProp="label"
                style={{ width: "100%" }}
              />
            </Space>
          </Col>

          <Col xs={24} md={12}>
            <Space orientation="vertical" style={{ width: "100%" }}>
              <Text strong>Statement</Text>
              <Select
                allowClear
                placeholder="Select statement"
                value={selectedStatementId}
                onChange={setSelectedStatementId}
                options={statementOptions}
                style={{ width: "100%" }}
              />
            </Space>
          </Col>
        </Row>

        <Space style={{ marginTop: 16 }}>
          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={runPreview}
            loading={loadingPreview}
          >
            Run Preview
          </Button>
          <Button icon={<ClearOutlined />} onClick={handleReset}>
            Reset
          </Button>
        </Space>
      </Card>

      {summary && (
        <Card style={{ borderRadius: 12 }}>
          <Row gutter={[12, 12]}>
            <Col>
              <Tag color="blue">
                Stock: {summary.stock_code || "-"}
                {summary.stock_name ? ` - ${summary.stock_name}` : ""}
              </Tag>
            </Col>
            <Col>
              <Tag color="purple">
                Statement: {summary.statement_name || "-"}
              </Tag>
            </Col>
            {summary.total_metrics !== undefined && (
              <Col>
                <Tag>Total Metrics: {summary.total_metrics}</Tag>
              </Col>
            )}
            {summary.total_dates !== undefined && (
              <Col>
                <Tag color="geekblue">Dates: {summary.total_dates}</Tag>
              </Col>
            )}
            {summary.total_rows !== undefined && (
              <Col>
                <Tag color="gold">Rows: {summary.total_rows}</Tag>
              </Col>
            )}
          </Row>
        </Card>
      )}

      <Card
        title={
          <Space>
            <TableOutlined />
            <span>Explorer Result</span>
          </Space>
        }
        extra={
          <ExportDropdown
            disabled={!canExport}
            onExportJson={() => {
              exportStockExplorerJson({
                summary,
                dateColumns,
                rows: exportRows,
              });
              message.success("JSON export started.");
            }}
            onExportCsv={() => {
              exportStockExplorerCsv({
                summary,
                dateColumns,
                rows: exportRows,
              });
              message.success("CSV export started.");
            }}
            onExportPdf={() => {
              exportStockExplorerPdf({
                summary,
                dateColumns,
                rows: exportRows,
              });
              message.success("PDF export started.");
            }}
          />
        }
        style={{ borderRadius: 12 }}
      >
        {tableRows.length > 0 ? (
          <Table
            rowKey="key"
            columns={tableColumns}
            dataSource={tableRows}
            loading={loadingPreview}
            pagination={false}
            expandable={{
              defaultExpandAllRows: false,
            }}
            scroll={{ x: "max-content" }}
            bordered={false}
            size="middle"
          />
        ) : (
          <Empty description="No data preview yet" />
        )}
      </Card>
    </Space>
  );
}