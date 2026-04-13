import { useState } from "react";

import PaginatedDataTable from "../../components/datatable/PaginatedDataTable";
import DimensionImportModal from "../../components/modal/DimensionImportModal";
import ImportExportAction from "../../components/action/ImportExport";
import useTableExport from "../../hooks/useTableExport";
import createStandardTableExporters from "../../utils/createStandardTableExporters";
import useServerTable from "../../hooks/useServerTable";
import { fetchStatements, importDimStatementCsv } from "../../services/stock_service";

export default function StatementsPage() {
  const [modalOpen, setModalOpen] = useState(false);
  const { data, total, loading, page, pageSize, handleTableChange, reload } =
    useServerTable(fetchStatements, 10);

  const columns = [
    { title: "Statement ID", dataIndex: "statement_id", key: "statement_id" },
    { title: "Statement Name", dataIndex: "statement_name", key: "statement_name" },
  ];

  const { exporting, runExport } = useTableExport(
    (pageNo, batchSize) => fetchStatements(pageNo, batchSize),
    {
      batchSize: 500,
      buildFilename: (fileType) => `statements.${fileType}`,
    }
  );

  const exportHandlers = createStandardTableExporters({
    runExport,
    columns,
    filenameBase: "statements",
    title: "Statements",
    subtitle: "Browse statement dimension records",
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
        title="Statements"
        subtitle="Browse statement dimension records"
        columns={columns}
        data={data}
        total={total}
        loading={loading}
        page={page}
        pageSize={pageSize}
        onChange={handleTableChange}
        rowKey="statement_id"
      />

      <DimensionImportModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={async () => {
          // setModalOpen(false);
          await reload(page, pageSize);
        }}
        title="Import Statement Dimension CSV"
        importFn={importDimStatementCsv}
      />  
    </>
  );
}