import React, { useEffect, useState } from "react";
import { Table, Button, Tag, Drawer, Input, Select, Space, Form, message } from "antd";
import { DownloadOutlined, ReloadOutlined } from "@ant-design/icons";
import * as XLSX from "xlsx";
import axios from "axios";


const statusOptions = ["Open", "In Progress", "Resolved", "Closed"];
const severityOptions = ["Low", "Medium", "High", "Critical"];

import { useNavigate } from "react-router-dom";

function getColumns(onView, filters, setFilters, submittedByOptions, navigate) {
  return [
    {
      title: "ID",
      dataIndex: "id",
      key: "id",
      render: (id, record) => (
        <a onClick={() => navigate(`/logs/bug-reports/${id}`)} style={{ cursor: "pointer" }}>{id}</a>
      ),
    },
    { title: "Title", dataIndex: "title", key: "title", filterDropdown: ({ setSelectedKeys, selectedKeys, confirm }) => (
      <Input
        placeholder="Search title"
        value={selectedKeys[0]}
        onChange={e => setSelectedKeys(e.target.value ? [e.target.value] : [])}
        onPressEnter={confirm}
        style={{ width: 150, marginBottom: 8, display: 'block' }}
      />
    ),
    onFilter: (value, record) => record.title?.toLowerCase().includes(value.toLowerCase()),
    },
    { title: "Status", dataIndex: "status", key: "status", filters: statusOptions.map(s => ({ text: s, value: s })),
      onFilter: (value, record) => record.status === value,
      render: (status) => <Tag>{status}</Tag> },
    { title: "Severity", dataIndex: "severity", key: "severity", filters: severityOptions.map(s => ({ text: s, value: s })),
      onFilter: (value, record) => record.severity === value },
    {
      title: "Submitted By",
      dataIndex: "submitted_by",
      key: "submitted_by",
      filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
        <Select
          mode="multiple"
          allowClear
          showSearch
          placeholder="Filter by submitter"
          style={{ minWidth: 180, maxWidth: 260 }}
          value={selectedKeys[0] ? selectedKeys[0].split(',') : []}
          onChange={values => setSelectedKeys(values.length ? [values.join(',')] : [])}
          onBlur={confirm}
          options={submittedByOptions.map(u => ({ label: u, value: u }))}
          filterOption={(input, option) => (option?.label ?? '').toLowerCase().includes(input.toLowerCase())}
        />
      ),
      filteredValue: filters.submitted_by ? [filters.submitted_by] : null,
      onFilter: (value, record) => {
        if (!value) return true;
        const selected = String(value).split(',');
        return selected.includes(record.submitted_by);
      },
      render: (val) => val || "—",
    },
    { title: "Assigned To", dataIndex: "assigned_to", key: "assigned_to" },
    { title: "Created At", dataIndex: "created_at", key: "created_at" },
    { title: "Actions", key: "actions", render: (_, record) => <Button onClick={() => onView(record)}>View</Button> },
  ];
}

export default function LogReportTable({ reports, loading, devMode, onUpdated }: { reports: any[]; loading: boolean; devMode?: boolean; onUpdated?: () => void }) {
  const [drawer, setDrawer] = useState({ open: false, record: null });
  const [form] = Form.useForm();
  const [updating, setUpdating] = useState(false);
  const [filters, setFilters] = useState({});
  const [submittedByFilter, setSubmittedByFilter] = useState(undefined);
  const navigate = useNavigate();

  // Collect unique "Submitted By" values for dropdown
  const submittedByOptions = Array.from(new Set(reports.map(r => r.submitted_by))).filter(Boolean);

  // Filter reports by selected user (if any)
  const filteredReports = submittedByFilter
    ? reports.filter(r => r.submitted_by === submittedByFilter)
    : reports;

  function onView(record: any) {
    setDrawer({ open: true, record });
    if (devMode) {
      form.setFieldsValue({
        status: record.status,
        comment: ""
      });
    }
  }

  // Excel Export
  function exportToExcel() {
    const worksheet = XLSX.utils.json_to_sheet(reports);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Log Reports");
    XLSX.writeFile(workbook, "log_reports.xlsx");
  }

  async function handleUpdate(values: any) {
    if (!drawer.record) return;
    setUpdating(true);
    try {
      const csrfToken = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrf_token='))
        ?.split('=')[1];
      await axios.patch(`/api/v1/log-reports/${drawer.record.id}`, {
        status: values.status,
        comment: values.comment
      }, {
        headers: { "X-CSRF-Token": csrfToken }
      });
      message.success("Report updated");
      setDrawer(d => ({ ...d, record: { ...d.record, status: values.status } }));
      if (onUpdated) onUpdated();
    } catch (e) {
      message.error("Failed to update report");
    } finally {
      setUpdating(false);
    }
  }

  return (
    <>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<DownloadOutlined />} onClick={exportToExcel}>Export Excel</Button>
      </Space>
      <div style={{ marginBottom: 16, maxWidth: 320 }}>
        <Select
          allowClear
          showSearch
          placeholder="Filter by Submitted By"
          style={{ width: '100%' }}
          value={submittedByFilter}
          onChange={setSubmittedByFilter}
          options={submittedByOptions.map(u => ({ label: u, value: u }))}
          filterOption={(input, option) => (option?.label ?? '').toLowerCase().includes(input.toLowerCase())}
        />
      </div>
      <Table
        columns={getColumns(onView, filters, setFilters, submittedByOptions, navigate)}
        dataSource={filteredReports}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />
      <Drawer open={drawer.open} onClose={() => setDrawer({ open: false, record: null })} size="large" style={{ width: 600 }} title="Log Report Details">
        {drawer.record && devMode ? (
          <Form
            form={form}
            layout="vertical"
            initialValues={{ status: drawer.record.status, comment: "" }}
            onFinish={handleUpdate}
          >
            <Form.Item label="Status" name="status" rules={[{ required: true }]}> 
              <Select options={statusOptions.map(s => ({ label: s, value: s }))} />
            </Form.Item>
            <Form.Item label="Comment" name="comment" rules={[{ required: false }]}> 
              <Input.TextArea rows={3} placeholder="Add a comment (optional)" />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={updating}>Update</Button>
            </Form.Item>
          </Form>
        ) : (
          <pre>{JSON.stringify(drawer.record, null, 2)}</pre>
        )}
      </Drawer>
    </>
  );
}
