import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Avatar,
  Button,
  Card,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import {
  EditOutlined,
  PlusOutlined,
  ReloadOutlined,
  UserOutlined,
  MergeCellsOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import {
  fetchUsersPaged,
  createUser,
  updateUser,
  activateUser,
  deactivateUser,
  setUserRoles,
  mergeUsers,
} from "@/features/admin/services/user_service";
import { fetchRoles } from "@/features/admin/services/role_service";
import { fetchDepartments } from "@/features/admin/services/department_service";
import { usePaginatedTable } from "@/shared/hooks/usePaginatedTable";
import { useIsAdmin } from "@/shared/hooks/useIsAdmin";

const { Title } = Typography;

export default function UserManagement() {
  const isAdmin = useIsAdmin();
  const fetcher = useCallback((params) => fetchUsersPaged(params), []);
  const {
    rows: users,
    loading,
    error,
    pagination,
    filters,
    sort,
    updateFilters,
    handleTableChange,
    loadData,
  } = usePaginatedTable({
    fetcher,
    defaultFilters: { search: "" },
    initialPageSize: 20,
  });

  const [roles, setRoles] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState(null);
  const [editingRoles, setEditingRoles] = useState(null);
  const [merging, setMerging] = useState(null);
  const [mergeDuplicateId, setMergeDuplicateId] = useState(null);
  const [mergeBusy, setMergeBusy] = useState(false);
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();
  const [rolesForm] = Form.useForm();

  useEffect(() => {
    fetchRoles().then(setRoles).catch(() => setRoles([]));
    fetchDepartments().then(setDepartments).catch(() => setDepartments([]));
  }, []);

  async function handleCreate(values) {
    try {
      await createUser(values);
      message.success("User created");
      setShowCreate(false);
      createForm.resetFields();
      loadData();
    } catch (e) {
      message.error(e.message || "Failed to create user");
    }
  }

  async function handleEdit(values) {
    try {
      await updateUser(editing.id, values);
      message.success("User updated");
      setEditing(null);
      loadData();
    } catch (e) {
      message.error(e.message || "Failed to update user");
    }
  }

  async function handleSetRoles(values) {
    try {
      await setUserRoles(editingRoles.id, values.role_ids || []);
      message.success("Roles updated");
      setEditingRoles(null);
      loadData();
    } catch (e) {
      message.error(e.message || "Failed to update roles");
    }
  }

  async function toggleActive(user) {
    if (!isAdmin) return;
    try {
      if (user.is_active) await deactivateUser(user.id);
      else await activateUser(user.id);
      loadData();
    } catch (e) {
      message.error(e.message || "Failed to toggle");
    }
  }

  async function handleMerge() {
    if (!merging || !mergeDuplicateId) return;
    if (mergeDuplicateId === merging.id) {
      message.error("Cannot merge a user with itself");
      return;
    }
    setMergeBusy(true);
    try {
      const result = await mergeUsers(merging.id, mergeDuplicateId);
      const moved = Object.entries(result?.transferred || {})
        .filter(([, n]) => n > 0)
        .map(([t, n]) => `${t}: ${n}`)
        .join(", ") || "no rows";
      message.success(`Merged. Repointed -> ${moved}`);
      setMerging(null);
      setMergeDuplicateId(null);
      loadData();
    } catch (e) {
      message.error(e.message || "Merge failed");
    } finally {
      setMergeBusy(false);
    }
  }

  function sortedFor(field) {
    if (sort?.sort_by !== field) return null;
    return sort.sort_order === "asc" ? "ascend" : "descend";
  }

  const columns = [
    {
      title: "ID",
      dataIndex: "id",
      width: 70,
      sorter: true,
      sortOrder: sortedFor("id"),
    },
    {
      title: "Employee ID",
      dataIndex: "employee_id",
      sorter: true,
      sortOrder: sortedFor("employee_id"),
      render: (v) => v || "\u2014",
    },
    {
      title: "Full Name",
      key: "full_name",
      sorter: true,
      sortOrder: sortedFor("full_name"),
      render: (_, r) => (
        <Space>
          <Avatar
            size="small"
            src={r.profile_picture_url || undefined}
            icon={!r.profile_picture_url ? <UserOutlined /> : undefined}
          />
          <span>{r.full_name || "\u2014"}</span>
        </Space>
      ),
    },
    {
      title: "Email",
      dataIndex: "email",
      sorter: true,
      sortOrder: sortedFor("email"),
    },
    {
      title: "Department",
      dataIndex: "department_id",
      sorter: true,
      sortOrder: sortedFor("department_id"),
      render: (v) => departments.find((d) => d.id === v)?.name || (v ?? "\u2014"),
    },
    {
      title: "Roles",
      key: "roles",
      render: (_, r) => {
        const rs = Array.isArray(r.roles) ? r.roles : [];
        if (rs.length === 0) return <Tag>none</Tag>;
        return (
          <Space size={[4, 4]} wrap>
            {rs.map((role) => (
              <Tag color="blue" key={role.id ?? role.role_name}>
                {role.role_name || String(role)}
              </Tag>
            ))}
          </Space>
        );
      },
    },
    {
      title: "Active",
      dataIndex: "is_active",
      width: 100,
      sorter: true,
      sortOrder: sortedFor("is_active"),
      render: (v, r) => (
        <Switch checked={v} onChange={() => toggleActive(r)} disabled={!isAdmin} />
      ),
    },
    {
      title: "Actions",
      key: "actions",
      width: 320,
      render: (_, r) => (
        <Space>
          <Tooltip title={isAdmin ? "" : "Admins only"}>
            <Button
              size="small"
              icon={<EditOutlined />}
              disabled={!isAdmin}
              onClick={() => {
                setEditing(r);
                editForm.setFieldsValue({
                  employee_id: r.employee_id,
                  email: r.email,
                  full_name: r.full_name,
                  department_id: r.department_id,
                });
              }}
            >
              Edit
            </Button>
          </Tooltip>
          <Tooltip title={isAdmin ? "" : "Admins only"}>
            <Button
              size="small"
              icon={<UserOutlined />}
              disabled={!isAdmin}
              onClick={() => {
                setEditingRoles(r);
                rolesForm.setFieldsValue({
                  role_ids: (r.roles || [])
                    .map((role) => role.id)
                    .filter((x) => x != null),
                });
              }}
            >
              Roles
            </Button>
          </Tooltip>
          <Tooltip title={isAdmin ? "" : "Admins only"}>
            <Button
              size="small"
              icon={<MergeCellsOutlined />}
              disabled={!isAdmin}
              onClick={() => {
                setMerging(r);
                setMergeDuplicateId(null);
              }}
            >
              Merge
            </Button>
          </Tooltip>
        </Space>
      ),
    },
  ];

  const mergeOptions = useMemo(
    () =>
      users
        .filter((u) => merging && u.id !== merging.id)
        .map((u) => ({
          value: u.id,
          label: `#${u.id} ${u.full_name || ""} ${u.email ? `<${u.email}>` : ""}`.trim(),
        })),
    [users, merging],
  );

  return (
    <Card>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 16,
          gap: 12,
          flexWrap: "wrap",
        }}
      >
        <Title level={3} style={{ margin: 0 }}>
          User Management
        </Title>
        <Space wrap>
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder="Search name, email, employee ID\u2026"
            value={filters.search}
            onChange={(e) => updateFilters({ search: e.target.value })}
            style={{ width: 320 }}
          />
          <Button icon={<ReloadOutlined />} onClick={() => loadData()}>
            Refresh
          </Button>
          <Tooltip title={isAdmin ? "" : "Admins only"}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setShowCreate(true)}
              disabled={!isAdmin}
            >
              New User
            </Button>
          </Tooltip>
        </Space>
      </div>

      {!isAdmin && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message="Read-only"
          description="Only administrators can create, edit, merge users or change roles."
        />
      )}
      {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} />}

      <Table
        rowKey="id"
        columns={columns}
        dataSource={users}
        loading={loading}
        pagination={{
          current: pagination.page,
          pageSize: pagination.page_size,
          total: pagination.total,
          showSizeChanger: true,
          showTotal: (t) => `Total ${t} records`,
        }}
        onChange={handleTableChange}
      />

      <Modal
        title="Create User"
        open={showCreate}
        onCancel={() => setShowCreate(false)}
        onOk={() => createForm.submit()}
        okText="Create"
      >
        <Form form={createForm} layout="vertical" onFinish={handleCreate}>
          <Form.Item name="full_name" label="Full Name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label="Email" rules={[{ required: true, type: "email" }]}>
            <Input />
          </Form.Item>
          <Form.Item name="employee_id" label="Employee ID">
            <Input />
          </Form.Item>
          <Form.Item name="department_id" label="Department">
            <Select allowClear options={departments.map((d) => ({ label: d.name, value: d.id }))} />
          </Form.Item>
          <Form.Item name="password" label="Password" rules={[{ required: true, min: 8 }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="is_active" label="Active" valuePropName="checked" initialValue={true}>
            <Switch />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`Edit User ${editing?.id || ""}`}
        open={!!editing}
        onCancel={() => setEditing(null)}
        onOk={() => editForm.submit()}
      >
        <Form form={editForm} layout="vertical" onFinish={handleEdit}>
          <Form.Item name="full_name" label="Full Name"><Input /></Form.Item>
          <Form.Item name="email" label="Email"><Input /></Form.Item>
          <Form.Item name="employee_id" label="Employee ID"><Input /></Form.Item>
          <Form.Item name="department_id" label="Department">
            <Select allowClear options={departments.map((d) => ({ label: d.name, value: d.id }))} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={`Assign Roles to ${editingRoles?.full_name || ""}`}
        open={!!editingRoles}
        onCancel={() => setEditingRoles(null)}
        onOk={() => rolesForm.submit()}
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message="Selected roles will replace all current roles for this user."
        />
        <Form form={rolesForm} layout="vertical" onFinish={handleSetRoles}>
          <Form.Item name="role_ids" label="Roles">
            <Select
              mode="multiple"
              options={roles.map((r) => ({ label: r.role_name, value: r.id }))}
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Merge Duplicate User"
        open={!!merging}
        onCancel={() => { setMerging(null); setMergeDuplicateId(null); }}
        onOk={handleMerge}
        okText="Merge"
        okButtonProps={{ danger: true, disabled: !mergeDuplicateId, loading: mergeBusy }}
        destroyOnHidden
      >
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 12 }}
          message="This action is irreversible"
          description={(
            <>
              All references to the duplicate user (roles, build requests,
              shipments, audit logs, etc.) will be repointed to the primary
              user. Conflicting unique rows will be dropped from the
              duplicate side. The duplicate user will then be deleted.
            </>
          )}
        />
        <Form layout="vertical">
          <Form.Item label="Primary (kept)">
            <Input
              disabled
              value={merging ? `#${merging.id} ${merging.full_name || ""} ${merging.email ? `<${merging.email}>` : ""}` : ""}
            />
          </Form.Item>
          <Form.Item label="Duplicate (will be deleted)" required>
            <Select
              showSearch
              placeholder="Select duplicate user"
              value={mergeDuplicateId}
              onChange={setMergeDuplicateId}
              options={mergeOptions}
              filterOption={(input, option) =>
                (option?.label || "").toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
