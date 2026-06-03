
import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, Typography, Button, Tag, Form, Select, Input, message, Spin } from "antd";
import axios from "axios";
import { useUserDisplayName } from "./useUserDisplayName";

const { Title, Paragraph } = Typography;
const statusOptions = ["Open", "In Progress", "Resolved", "Closed"];

export default function BugReportView() {
  const { reportId } = useParams();
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  // Simulate user role (replace with real auth logic)
  const isAdmin = window.localStorage.getItem("role") === "Admin";

  // User-friendly names
  const submittedByName = useUserDisplayName(report?.submitted_by);
  const assignedToName = useUserDisplayName(report?.assigned_to);

  useEffect(() => {
    setLoading(true);
    axios.get(`/api/v1/log-reports/${reportId}`)
      .then(res => setReport(res.data))
      .catch(() => message.error("Failed to load bug report"))
      .finally(() => setLoading(false));
  }, [reportId]);

  const handleEdit = () => {
    setEditMode(true);
    form.setFieldsValue({ status: report.status, comment: "" });
  };

  const handleUpdate = async (values: any) => {
    setUpdating(true);
    try {
      const csrfToken = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrf_token='))
        ?.split('=')[1];
      await axios.patch(`/api/v1/log-reports/${reportId}`, {
        status: values.status,
        comment: values.comment
      }, {
        headers: { "X-CSRF-Token": csrfToken }
      });
      message.success("Report updated");
      setReport({ ...report, status: values.status });
      setEditMode(false);
    } catch {
      message.error("Failed to update report");
    } finally {
      setUpdating(false);
    }
  };

  if (loading) return <Spin />;
  if (!report) return <Paragraph>Not found.</Paragraph>;

  return (
    <Card style={{ maxWidth: 700, margin: "0 auto", marginTop: 32 }}>
      <Title level={3}>Bug Report Details</Title>
      <Paragraph><b>Bug ID:</b> {report.id}</Paragraph>
      <Paragraph><b>Title:</b> {report.title}</Paragraph>
      <Paragraph><b>Description:</b> {report.description}</Paragraph>
      <Paragraph><b>Page/Module:</b> {report.page || <i>Not specified</i>}</Paragraph>
      <Paragraph><b>Steps to Reproduce:</b> {report.steps_to_reproduce || <i>Not specified</i>}</Paragraph>
      <Paragraph><b>Expected Behavior:</b> {report.expected_behavior || <i>Not specified</i>}</Paragraph>
      <Paragraph><b>Actual Behavior:</b> {report.actual_behavior || <i>Not specified</i>}</Paragraph>
      <Paragraph><b>Severity:</b> <Tag>{report.severity}</Tag></Paragraph>
      <Paragraph><b>Status:</b> <Tag>{report.status}</Tag></Paragraph>
      <Paragraph><b>Submitted By:</b> {submittedByName || report.submitted_by}</Paragraph>
      <Paragraph><b>Assigned To:</b> {assignedToName || (report.assigned_to || <i>Not assigned</i>)}</Paragraph>
      <Paragraph><b>Created At:</b> {report.created_at}</Paragraph>
      <Paragraph><b>Updated At:</b> {report.updated_at}</Paragraph>
      {report.attachments && report.attachments.length > 0 ? (
        <Paragraph>
          <b>Attachments:</b><br />
          {report.attachments.map((att: any) => {
            const url = att.file_url;
            const imageExts = [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"];
            const ext = url.substring(url.lastIndexOf(".")).toLowerCase();
            if (imageExts.includes(ext)) {
              return (
                <img
                  key={att.id}
                  src={url}
                  alt="Attachment"
                  style={{
                    maxWidth: "100%",
                    height: "auto",
                    border: "1px solid #ccc",
                    borderRadius: 6,
                    marginTop: 8,
                    marginBottom: 8,
                    boxShadow: "0 2px 8px #f0f1f2"
                  }}
                />
              );
            } else {
              const filename = url.split("/").pop();
              return <div key={att.id}><a href={url} target="_blank" rel="noopener noreferrer">Download {filename}</a></div>;
            }
          })}
        </Paragraph>
      ) : (
        <Paragraph><i>No attachments uploaded for this bug report.</i></Paragraph>
      )}
      <Paragraph><b>Developer Notes:</b> {report.developer_notes || <i>None</i>}</Paragraph>
      {isAdmin && !editMode && (
        <Button type="primary" onClick={handleEdit} style={{ marginTop: 16 }}>Edit</Button>
      )}
      {editMode && (
        <Form form={form} layout="vertical" onFinish={handleUpdate} style={{ marginTop: 24 }}>
          <Form.Item label="Status" name="status" rules={[{ required: true }]}> 
            <Select options={statusOptions.map(s => ({ label: s, value: s }))} />
          </Form.Item>
          <Form.Item label="Comment" name="comment">
            <Input.TextArea rows={3} placeholder="Add a comment (optional)" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={updating}>Update</Button>
            <Button style={{ marginLeft: 8 }} onClick={() => setEditMode(false)}>Cancel</Button>
          </Form.Item>
        </Form>
      )}
      <Button style={{ marginTop: 16 }} onClick={() => navigate(-1)}>Back</Button>
    </Card>
  );
}
