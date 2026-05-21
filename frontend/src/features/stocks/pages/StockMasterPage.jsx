import { useState } from "react";

import PaginatedDataTable from "@/shared/components/PaginatedDataTable";
import DimensionImportModal from "@/features/stocks/components/DimensionImportModal";
import ImportExportAction from "@/shared/components/ImportExport";
import useServerTable from "@/shared/hooks/useServerTable";
import useTableExport from "@/shared/hooks/useTableExport";
import { fetchStockMaster, importDimStockCsv } from "@/features/stocks/services/stock_service";
import createStandardTableExporters from "@/shared/utils/createStandardTableExporters";

export default function StockMasterPage() {
  const [modalOpen, setModalOpen] = useState(false);

  const {
    data,
    total,
    loading,
    page,
    pageSize,
    handleTableChange,
    reload,
  } = useServerTable(fetchStockMaster, 10);

  const columns = [
    { title: "Stock ID", dataIndex: "stock_id", key: "stock_id", sorter: true },
    { title: "Stock Code", dataIndex: "stock_code", key: "stock_code", sorter: true },
    { title: "Stock Number", dataIndex: "stock_number", key: "stock_number", sorter: true },
    { title: "Stock Name", dataIndex: "stock_name", key: "stock_name", sorter: true },
    {
      title: "Weblink",
      dataIndex: "weblink",
      key: "weblink",
      render: (value) =>
        value ? (
          <a href={value} target="_blank" rel="noreferrer">
            {value}
          </a>
        ) : (
          "-"
        ),
    },
    { title: "Price", dataIndex: "price", key: "price", sorter: true },
  ];

  const { exporting, runExport } = useTableExport(
    (pageNo, batchSize) => fetchStockMaster(pageNo, batchSize),
    {
      batchSize: 500,
      buildFilename: (fileType) => `stocks.${fileType}`,
    }
  );

  const exportHandlers = createStandardTableExporters({
    runExport,
    columns,
    filenameBase: "stock_master",
    title: "Stock Master",
    subtitle: "Browse stock dimension records",
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
        title="Stock Master"
        subtitle="Browse stock dimension records"
        columns={columns}
        data={data}
        total={total}
        loading={loading}
        page={page}
        pageSize={pageSize}
        onChange={handleTableChange}
        rowKey="stock_id"
      />

      <DimensionImportModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSuccess={async () => {
          await reload(page, pageSize);
        }}
        title="Import Stock Dimension CSV"
        importFn={importDimStockCsv}
      />
    </>
  );
}