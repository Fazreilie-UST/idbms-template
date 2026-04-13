import PaginatedDataTable from "../../components/datatable/PaginatedDataTable";
import useServerTable from "../../hooks/useServerTable";
import { fetchFinancialFacts } from "../../services/stock_service";
import ImportCsvModal from "../../components/modal/FactImportModal";
import ImportExportAction from "../../components/action/ImportExport";
import useTableExport from "../../hooks/useTableExport";
import createStandardTableExporters from "../../utils/createStandardTableExporters";
import { useState } from "react";

export default function FinancialFactsPage() {
  const [modalOpen, setModalOpen] = useState(false);

  const { data, total, loading, page, pageSize, handleTableChange, reload } =
    useServerTable(fetchFinancialFacts, 10);

  const columns = [
    {
      title: "Stock ID",
      dataIndex: "stock_id",
      key: "stock_id",
      sorter: true,
    },
    {
      title: "Metric ID",
      dataIndex: "metric_id",
      key: "metric_id",
      sorter: true,
    },
    {
      title: "Statement ID",
      dataIndex: "statement_id",
      key: "statement_id",
      sorter: true,
    },
    {
      title: "Date ID",
      dataIndex: "date_id",
      key: "date_id",
      sorter: true,
    },
    {
      title: "Value",
      dataIndex: "value",
      key: "value",
    },
  ];

  const { exporting, runExport } = useTableExport(
    (pageNo, batchSize) => fetchFinancialFacts(pageNo, batchSize),
    {
      batchSize: 500,
      buildFilename: (fileType) => `financial_facts.${fileType}`,
    }
  );

  const exportHandlers = createStandardTableExporters({
    runExport,
    columns,
    filenameBase: "financial_facts",
    title: "Financial Facts",
    subtitle: "Browse financial fact records",
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
        title="Financial Facts"
        subtitle="Browse fact financial value records"
        columns={columns}
        data={data}
        total={total}
        loading={loading}
        page={page}
        pageSize={pageSize}
        onChange={handleTableChange}
        rowKey={(record) =>
          `${record.stock_id}-${record.metric_id}-${record.statement_id}-${record.date_id}`
        }
      />

      <ImportCsvModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={async () => {
          await reload(page, pageSize);
        }}
      />
    </>
  );
}