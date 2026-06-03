import React, { useEffect, useState, forwardRef, useImperativeHandle } from "react";
import { Table, Select, DatePicker, Button, Drawer, Space } from "antd";
import { DownloadOutlined, ReloadOutlined } from "@ant-design/icons";
import * as XLSX from "xlsx";
import axios from "axios";

const { Option } = Select;

const { RangePicker } = DatePicker;


function getColumns(onView) {
  return [
    { title: "Timestamp", dataIndex: "created_at", key: "created_at" },
    { title: "User", dataIndex: "user_id", key: "user_id" },
    { title: "Module", dataIndex: "module", key: "module" },
    { title: "Action", dataIndex: "action", key: "action" },
    { title: "Record ID", dataIndex: "record_id", key: "record_id" },
    { title: "IP", dataIndex: "ip_address", key: "ip_address" },
    { title: "Details", key: "details", render: (_, record) => <Button onClick={() => onView(record)}>View</Button> },
  ];
}

const AuditLogTable = forwardRef(function AuditLogTable(_, ref) {
  const [logs, setLogs] = useState([]);
  const [filters, setFilters] = useState({});
  const [drawer, setDrawer] = useState({ open: false, record: null });
  const [loading, setLoading] = useState(false);
  const [filterOptions, setFilterOptions] = useState({
    user_ids: [],
    actions: [],
    modules: [],
    ip_addresses: [],
  });
  // Fetch filter options for dropdowns
  useEffect(() => {
    axios.get("/api/v1/audit-logs/filters").then(res => {
      setFilterOptions(res.data || {});
    });
  }, []);


  const fetchLogs = () => {
    setLoading(true);
    axios.get("/api/v1/audit-logs", { params: filters }).then(res => {
      const data = Array.isArray(res.data) ? res.data : [];
      // Sort by created_at descending (latest first)
      data.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
      setLogs(data.map((log: any) => ({ ...log })));
    }).finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchLogs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  useImperativeHandle(ref, () => ({
    refresh: fetchLogs
  }));

  function onView(record: any) {
    setDrawer({ open: true, record });
  }


  // Excel Export
  function exportToExcel() {
    const worksheet = XLSX.utils.json_to_sheet(logs);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Audit Logs");
    XLSX.writeFile(workbook, "audit_logs.xlsx");
  }

  return (
    <>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<DownloadOutlined />} onClick={exportToExcel}>Export Excel</Button>
        <Button icon={<ReloadOutlined />} onClick={() => window.location.reload()}>Refresh</Button>
      </Space>
      <div style={{ marginBottom: 16, display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <RangePicker onChange={dates => setFilters(f => ({ ...f, start_date: dates?.[0]?.toISOString(), end_date: dates?.[1]?.toISOString() }))} />
        <Select
          allowClear
          showSearch
          placeholder="User ID"
          style={{ width: 140 }}
          value={filters.user_id || undefined}
          onChange={value => setFilters(f => ({ ...f, user_id: value }))}
          options={filterOptions.user_ids.map(id => ({ label: id, value: id }))}
        />
        <Select
          allowClear
          showSearch
          placeholder="Action"
          style={{ width: 140 }}
          value={filters.action || undefined}
          onChange={value => setFilters(f => ({ ...f, action: value }))}
          options={filterOptions.actions.map(a => ({ label: a, value: a }))}
        />
        <Select
          allowClear
          showSearch
          placeholder="Entity"
          style={{ width: 140 }}
          value={filters.module || undefined}
          onChange={value => setFilters(f => ({ ...f, module: value }))}
          options={filterOptions.modules.map(m => ({ label: m, value: m }))}
        />
        <Select
          allowClear
          showSearch
          placeholder="IP"
          style={{ width: 140 }}
          value={filters.ip_address || undefined}
          onChange={value => setFilters(f => ({ ...f, ip_address: value }))}
          options={filterOptions.ip_addresses.map(ip => ({ label: ip, value: ip }))}
        />
        <Button onClick={() => setFilters({})}>Reset</Button>
      </div>
      <Table
        columns={getColumns(onView)}
        dataSource={logs}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 15 }}
      />
      <Drawer open={drawer.open} onClose={() => setDrawer({ open: false, record: null })} width={600} title="Audit Log Details">
        {drawer.record && (
          <div>
            <div><b>ID:</b> {drawer.record.id}</div>
            <div><b>User ID:</b> {drawer.record.user_id}</div>
            <div><b>Module:</b> {drawer.record.module}</div>
            <div><b>Action:</b> {drawer.record.action}</div>
            <div><b>Record ID:</b> {drawer.record.record_id}</div>
            <div><b>Created At:</b> {drawer.record.created_at}</div>
            <div><b>IP Address:</b> {drawer.record.ip_address}</div>
            <div><b>User Agent:</b> {drawer.record.user_agent}</div>
            <div><b>Old Value:</b> <pre>{JSON.stringify(drawer.record.old_value, null, 2)}</pre></div>
            <div><b>New Value:</b> <pre>{JSON.stringify(drawer.record.new_value, null, 2)}</pre></div>
          </div>
        )}
      </Drawer>
    </>
  );
});

export default AuditLogTable;
