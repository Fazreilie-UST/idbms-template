import { useEffect } from "react";
import {
  Alert,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Typography,
} from "antd";

const { Paragraph, Text } = Typography;

// Subset of BuildPlanStatus values writable from the UI. Backend still
// enforces monotonic transitions and which statuses allow manual edits.
const STATUS_OPTIONS = [
  { value: "New", label: "New" },
  { value: "Plan", label: "Plan" },
  { value: "Hold", label: "Hold" },
  { value: "Done", label: "Done" },
  { value: "Cancelled", label: "Cancelled" },
];

function snapshotPlan(latestRevision) {
  return (latestRevision?.snapshot?.plan) || {};
}

export default function AddRevisionModal({
  open,
  onClose,
  onSubmit,
  submitting,
  latestRevision,
}) {
  const [form] = Form.useForm();

  useEffect(() => {
    if (!open) return;
    const plan = snapshotPlan(latestRevision);
    form.setFieldsValue({
      status: plan.status || "New",
      support_activity: plan.support_activity || "",
      build_description: plan.build_description || "",
      product_code: plan.product_code || "",
      mm_number: plan.mm_number || "",
      ta_number: plan.ta_number || "",
      pba_number: plan.pba_number || "",
      as_number: plan.as_number || "",
      special_instruction: plan.special_instruction || "",
      required_quantity: plan.required_quantity ?? null,
      estimated_yield: plan.estimated_yield ?? null,
      build_start_quantity: plan.build_start_quantity ?? null,
      build_notes: (plan.build_notes || []).join(", "),
    });
  }, [open, latestRevision, form]);

  const handleOk = async () => {
    const values = await form.validateFields();
    const payload = {
      status: values.status,
      support_activity: values.support_activity?.trim() || null,
      build_description: values.build_description?.trim() || null,
      product_code: values.product_code?.trim() || null,
      mm_number: values.mm_number?.trim() || null,
      ta_number: values.ta_number?.trim() || null,
      pba_number: values.pba_number?.trim() || null,
      as_number: values.as_number?.trim() || null,
      special_instruction: values.special_instruction?.trim() || null,
      required_quantity:
        values.required_quantity === undefined ||
        values.required_quantity === null ||
        values.required_quantity === ""
          ? null
          : Number(values.required_quantity),
      estimated_yield:
        values.estimated_yield === undefined ||
        values.estimated_yield === null ||
        values.estimated_yield === ""
          ? null
          : Number(values.estimated_yield),
      build_start_quantity:
        values.build_start_quantity === undefined ||
        values.build_start_quantity === null ||
        values.build_start_quantity === ""
          ? null
          : Number(values.build_start_quantity),
      build_notes: (values.build_notes || "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    };
    onSubmit(payload);
  };

  return (
    <Modal
      title="Add New Revision"
      open={open}
      onCancel={onClose}
      onOk={handleOk}
      confirmLoading={submitting}
      okText="Create Revision"
      width={720}
      destroyOnHidden
    >
      <Alert
        type="info"
        showIcon
        message="Scalar field edits only"
        description="Component, test, build-request, and warehouse-quantity changes must come from re-importing the build plan file. This form only changes plan-level fields and status."
        style={{ marginBottom: 16 }}
      />

      <Form form={form} layout="vertical">
        <Form.Item
          label="Status"
          name="status"
          rules={[{ required: true, message: "Status is required" }]}
        >
          <Select options={STATUS_OPTIONS} />
        </Form.Item>

        <Form.Item label="Support Activity" name="support_activity">
          <Input placeholder="e.g. Integration" />
        </Form.Item>

        <Form.Item label="Build Description" name="build_description">
          <Input />
        </Form.Item>

        <Form.Item label="Product Code" name="product_code">
          <Input />
        </Form.Item>

        <Form.Item label="MM Number" name="mm_number">
          <Input />
        </Form.Item>

        <Form.Item label="TA Number" name="ta_number">
          <Input />
        </Form.Item>

        <Form.Item label="PBA Number" name="pba_number">
          <Input />
        </Form.Item>

        <Form.Item label="AS Number" name="as_number">
          <Input />
        </Form.Item>

        <Form.Item label="Special Instruction" name="special_instruction">
          <Input.TextArea autoSize={{ minRows: 2, maxRows: 4 }} />
        </Form.Item>

        <Form.Item label="Required Quantity" name="required_quantity">
          <InputNumber min={0} style={{ width: "100%" }} />
        </Form.Item>

        <Form.Item label="Build Start Quantity" name="build_start_quantity">
          <InputNumber min={0} style={{ width: "100%" }} />
        </Form.Item>

        <Form.Item label="Estimated Yield (%)" name="estimated_yield">
          <InputNumber min={0} max={100} style={{ width: "100%" }} />
        </Form.Item>

        <Form.Item
          label="Build Notes"
          name="build_notes"
          extra="Comma-separated"
        >
          <Input placeholder="e.g. SI, EMI, Functional" />
        </Form.Item>
      </Form>

      <Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 0 }}>
        <Text strong>Note:</Text> If no fields change vs. the latest revision,
        no new revision will be created.
      </Paragraph>
    </Modal>
  );
}
