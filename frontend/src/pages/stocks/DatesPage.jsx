import { useState } from "react";

import PaginatedDataTable from "../../components/datatable/PaginatedDataTable";
import DimensionImportModal from "../../components/modal/DimensionImportModal";
import ImportExportAction from "../../components/action/ImportExport";
import useServerTable from "../../hooks/useServerTable";
import useTableExport from "../../hooks/useTableExport";
import { fetchDates, importDimDateCsv } from "../../services/stock_service";
import { API } from "../../config";
import createStandardTableExporters from "../../utils/createStandardTableExporters";

export default function DatesPage() {
  const [modalOpen, setModalOpen] = useState(false);

  const {
    data,
    total,
    loading,
    page,
    pageSize,
    handleTableChange,
    reload,
  } = useServerTable(fetchDates, 10);

  const columns = [
    { title: "Date ID", dataIndex: "date_id", key: "date_id" },
    { title: "Full Date", dataIndex: "full_date", key: "full_date" },
    { title: "Year", dataIndex: "year", key: "year" },
    { title: "Month", dataIndex: "month", key: "month" },
  ];

  const { exporting, runExport } = useTableExport(
    (pageNo, batchSize) => fetchDates(pageNo, batchSize),
    {
      batchSize: 500,
      buildFilename: (fileType) => `dates.${fileType}`,
    }
  );

  const exportHandlers = createStandardTableExporters({
    runExport,
    columns,
    filenameBase: "dates",
    title: "Dates",
    subtitle: "Browse date dimension records",
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
        title="Dates"
        subtitle="Browse date dimension records"
        columns={columns}
        data={data}
        total={total}
        loading={loading}
        page={page}
        pageSize={pageSize}
        onChange={handleTableChange}
        rowKey="date_id"
      />

      <DimensionImportModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={async () => {
          await reload(page, pageSize);
        }}
        title="Import Date Dimension CSV"
        importFn={importDimDateCsv}
        sampleUrl={`${API}/stocks/dates/import-csv/sample`}
      />
    </>
  );
}