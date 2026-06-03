import React, { useState } from "react";
import { Form, Input, Button, Select, Upload, message } from "antd";
import axios from "axios";

const { Option } = Select;

export default function LogReportForm({ onSubmitted, onAuditRefresh }: { onSubmitted?: () => void, onAuditRefresh?: () => void }) {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  const onFinish = async (values: any) => {
    setLoading(true);
    try {
      // AntD Upload stores files as an array in file
      let files: File[] = [];
      if (values.file && Array.isArray(values.file) && values.file.length > 0) {
        files = values.file.map((f: any) => f.originFileObj).filter(Boolean);
      }
      // Client-side file size validation (max 5MB per file)
      const MAX_SIZE = 5 * 1024 * 1024;
      const tooLarge = files.find(f => f.size > MAX_SIZE);
      if (tooLarge) {
        message.error(`Attachment "${tooLarge.name}" is too large (max 5MB). Please remove it before submitting.`);
        setLoading(false);
        return;
      }
      const { file: _ignored, ...rest } = values;
      // Get CSRF token from cookie
      const csrfToken = document.cookie
        .split('; ')
        .find(row => row.startsWith('csrf_token='))
        ?.split('=')[1];

      const res = await axios.post("/api/v1/log-reports", rest, {
        headers: { "X-CSRF-Token": csrfToken }
      });
      let attachmentError = false;
      if (files.length > 0) {
        for (const file of files) {
          const formData = new FormData();
          formData.append("file", file);
          try {
            await axios.post(`/api/v1/log-reports/${res.data.id}/attachments`, formData, {
              headers: { "X-CSRF-Token": csrfToken }
            });
          } catch (err) {
            attachmentError = true;
            message.error("Attachment upload failed: " + (err?.response?.data?.detail || err));
          }
        }
      } else {
        // No files to upload
      }
      message.success("Report submitted");
      if (attachmentError) message.warning("Report submitted, but attachment upload failed.");
      form.resetFields();
      if (onSubmitted) onSubmitted();
      if (onAuditRefresh) onAuditRefresh();
      if (files.length > 0 && !attachmentError) {
        message.success("All attachments uploaded!");
      }
    } catch (e: any) {
      // Log error for debugging
      console.error("Report submission error", e);
      // Show backend error message if available
      if (e.response && e.response.data && (e.response.data.detail || e.response.data.message)) {
        message.error(e.response.data.detail || e.response.data.message);
      } else {
        message.error("Failed to submit report");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form layout="vertical" form={form} onFinish={onFinish} style={{ maxWidth: 600 }}>
      <Form.Item
        name="title"
        label="Title"
        rules={[{ required: true, message: "Please enter a title" }]}
        hasFeedback
        validateTrigger={["onChange", "onBlur"]}
      >
        <Input placeholder="Enter title" />
      </Form.Item>
      <Form.Item
        name="description"
        label="Description"
        rules={[{ required: true, message: "Please enter a description" }]}
        hasFeedback
        validateTrigger={["onChange", "onBlur"]}
      >
        <Input.TextArea rows={4} placeholder="Enter description" />
      </Form.Item>
      <Form.Item name="page" label="Page/Module"> <Input /> </Form.Item>
      <Form.Item name="steps_to_reproduce" label="Steps to Reproduce"> <Input.TextArea rows={2} /> </Form.Item>
      <Form.Item name="expected_behavior" label="Expected Behavior"> <Input /> </Form.Item>
      <Form.Item name="actual_behavior" label="Actual Behavior"> <Input /> </Form.Item>
      <Form.Item
        name="severity"
        label="Severity"
        rules={[{ required: true, message: "Please select a severity" }]}
        hasFeedback
        validateTrigger={["onChange", "onBlur"]}
      >
        <Select placeholder="Select severity">
          <Option value="Low">Low</Option>
          <Option value="Medium">Medium</Option>
          <Option value="High">High</Option>
          <Option value="Critical">Critical</Option>
        </Select>
      </Form.Item>
      <Form.Item
        name="file"
        label="Screenshots/Attachments"
        valuePropName="fileList"
        getValueFromEvent={e => Array.isArray(e) ? e : e && e.fileList}
      >
        <Upload beforeUpload={() => false} multiple>
          <Button>Upload</Button>
        </Upload>
      </Form.Item>
      <Form.Item> <Button type="primary" htmlType="submit" loading={loading}>Submit</Button> </Form.Item>
    </Form>
  );
}
