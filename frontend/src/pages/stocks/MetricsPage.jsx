import { useState } from "react";

import PaginatedDataTable from "../../components/datatable/PaginatedDataTable";
import DimensionImportModal from "../../components/modal/DimensionImportModal";
import ImportExportAction from "../../components/action/ImportExport";
import useTableExport from "../../hooks/useTableExport";
import createStandardTableExporters from "../../utils/createStandardTableExporters";
import useServerTable from "../../hooks/useServerTable";
import { fetchMetrics, importDimMetricCsv } from "../../services/stock_service";

export default function MetricsPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const { data, 
    total, 
    loading, 
    page, 
    pageSize, 
    handleTableChange,
    reload 
  } = useServerTable(fetchMetrics, 10);

  const columns = [
    { title: "Metric ID", dataIndex: "metric_id", key: "metric_id" },
    { title: "Metric Name", dataIndex: "metric_name", key: "metric_name" },
    { title: "Statement ID", dataIndex: "statement_id", key: "statement_id" },
    { title: "Parent Metric ID", dataIndex: "parent_metric_id", key: "parent_metric_id" },
  ];

  const { exporting, runExport } = useTableExport(
    (pageNo, batchSize) => fetchMetrics(pageNo, batchSize),
    {
      batchSize: 500,
      buildFilename: (fileType) => `metrics.${fileType}`,
    }
  );
  
  const exportHandlers = createStandardTableExporters({
    runExport,
    columns,
    filenameBase: "metrics",
    title: "Metrics",
    subtitle: "Browse financial metric dimension records",
  });

  return (
    <>
      <ImportExportAction
        importLabel="Add Data"
        onImport={() => setModalOpen(true)}
        exporting={exporting}
        {...exportHandlers}
      />

      <PaginatedDataTable
        title="Metrics"
        subtitle="Browse financial metric dimension records"
        columns={columns}
        data={data}
        total={total}
        loading={loading}
        page={page}
        pageSize={pageSize}
        onChange={handleTableChange}
        rowKey="metric_id"
      />

      <DimensionImportModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={async () => {
          // setModalOpen(false);
          await reload(page, pageSize);
        }}
        title="Import Metric Dimension CSV"
        importFn={importDimMetricCsv}
      />
    </>
  );
}