import { useEffect, useState, useMemo } from "react";
import {
  Alert,
  Button,
  Card,
  Form,
  Input,
  List,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import { DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined, SafetyOutlined } from "@ant-design/icons";
import {
  fetchRoles,
  createRole,
  updateRole,
  deleteRole,
  setRolePermissions,
  fetchPermissions,
} from "@/features/admin/services/role_service";

const { Title, Text } = Typography;

export default function RoleManagement() {
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState(null);
  const [permEditing, setPermEditing] = useState(null);
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const [permForm] = Form.useForm();

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [r, p] = await Promise.all([
        fetchRoles(),
        fetchPermissions().catch(() => []),
      ]);
      setRoles(r || []);
      setPermissions(p || []);
    } catch (e) {
      setError(e.message || "Failed to load roles");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const permissionsByCategory = useMemo(() => {
    const groups = {};
    for (const p of permissions) {
      const key = p.action_category_name || "Uncategorized";
      groups[key] ||= [];
      groups[key].push(p);
    }
    return groups;
  }, [permissions]);

  async function handleCreate(values) {
    try {
      await createRole(values);
      message.success("Role created");
      setCreating(false);
      createForm.resetFields();
      load();
    } catch (e) {
      message.error(e.message || "Failed");
    }
  }

  async function handleEdit(values) {
    try {
      await updateRole(editing.id, values);
      message.success("Role updated");
      setEditing(null);
      load();
    } catch (e) {
      message.error(e.message || "Failed");
    }
  }

  async function handleDelete(role) {
    try {
      await deleteRole(role.id);
      message.success("Role deleted");
      load();
    } catch (e) {
      message.error(e.message || "Failed");
    }
  }

  async function handleSavePerms(values) {
    try {
      await setRolePermissions(permEditing.id, values.permission_ids || []);
      message.success("Permissions updated");
      setPermEditing(null);
      load();
    } catch (e) {
      message.error(e.message || "Failed");
    }
  }

  const columns = [
    { title: "ID", dataIndex: "id", width: 70 },
    { title: "Role", dataIndex: "role_name" },
    { title: "Description", dataIndex: "description", render: (v) => v || "—" },
    {
      title: "Permissions",
      key: "perms",
      render: (_, r) => (
        <Space size={[4, 4]} wrap>
          {(r.permissions || []).slice(0, 6).map((p) => (
            <Tag key={p.id}>{p.code}</Tag>
          ))}
          {(r.permissions || []).length > 6 && <Tag>+{r.permissions.length - 6} more</Tag>}
          {(r.permissions || []).length === 0 && <Text type="secondary">none</Text>}
        </Space>
      ),
    },
    {
      title: "Actions",
      key: "actions",
      width: 280,
      render: (_, r) => (
        <Space>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => {
              setEditing(r);
              editForm.setFieldsValue({
                role_name: r.role_name,
                description: r.description,
              });
            }}
          >
            Edit
          </Button>
          <Button
            size="small"
            icon={<SafetyOutlined />}
            onClick={() => {
              setPermEditing(r);
              permForm.setFieldsValue({
                permission_ids: (r.permissions || []).map((p) => p.id),
              });
            }}
          >
            Permissions
          </Button>
          <Popconfirm title="Delete role?" onConfirm={() => handleDelete(r)} okButtonProps={{ danger: true }}>
            <Button size="small" danger icon={<DeleteOutlined />}>Delete</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>Role Management</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load}>Refresh</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreating(true)}>New Role</Button>
        </Space>
      </div>

      {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} />}

      <Table rowKey="id" columns={columns} dataSource={roles} loading={loading} pagination={false} />

      <Modal title="Create Role" open={creating} onCancel={() => setCreating(false)} onOk={() => createForm.submit()}>
        <Form form={createForm} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="role_name" label="Role Name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="description" label="Description"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>

      <Modal title={`Edit Role ${editing?.id || ""}`} open={!!editing} onCancel={() => setEditing(null)} onOk={() => editForm.submit()}>
        <Form form={editForm} layout="vertical" onFinish={handleEdit}>
          <Form.Item name="role_name" label="Role Name"><Input /></Form.Item>
          <Form.Item name="description" label="Description"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`Manage permissions for "${permEditing?.role_name || ""}"`}
        open={!!permEditing}
        onCancel={() => setPermEditing(null)}
        onOk={() => permForm.submit()}
        width={720}
      >
        <Alert type="info" showIcon style={{ marginBottom: 12 }}
          message="Users in this role will need to log in again after saving." />
        <Form form={permForm} layout="vertical" onFinish={handleSavePerms}>
          <Form.Item name="permission_ids" label="Permissions">
            <Select
              mode="multiple"
              showSearch
              optionFilterProp="label"
              placeholder="Select permissions"
              options={Object.entries(permissionsByCategory).map(([cat, perms]) => ({
                label: cat,
                title: cat,
                options: perms.map((p) => ({ label: `${p.code} — ${p.name}`, value: p.id })),
              }))}
            />
          </Form.Item>
        </Form>
        {permissions.length === 0 && (
          <Text type="secondary">No permissions defined yet. Seed permissions in the database first.</Text>
        )}
      </Modal>
    </Card>
  );
}
