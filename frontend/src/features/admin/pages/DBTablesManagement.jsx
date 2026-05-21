import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Drawer,
  Empty,
  Form,
  Input,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Switch,
  Table,
  Tabs,
  Tag,
  Tooltip,
  Typography,
  message,
} from "antd";
import {
  DeleteOutlined,
  EditOutlined,
  PlusOutlined,
  ReloadOutlined,
  TeamOutlined,
  MergeCellsOutlined,
  SearchOutlined,
} from "@ant-design/icons";
import {
  fetchDepartments,
  createDepartment,
  updateDepartment,
  deleteDepartment,
} from "@/features/admin/services/department_service";
import {
  fetchForwarders,
  createForwarder,
  updateForwarder,
  deleteForwarder,
  fetchBuildNotes,
  createBuildNote,
  updateBuildNote,
  deleteBuildNote,
  mergeBuildNotes,
  fetchSupportActivities,
  createSupportActivity,
  updateSupportActivity,
  deleteSupportActivity,
  fetchFormFactors,
  createFormFactor,
  updateFormFactor,
  deleteFormFactor,
  fetchSiliconSteppings,
  createSiliconStepping,
  updateSiliconStepping,
  deleteSiliconStepping,
  createComponent,
  updateComponent,
  deleteComponent,
  fetchSuppliers,
  createSupplier,
  updateSupplier,
  deleteSupplier,
  fetchComponentSupplierTree,
  addComponentSupplier,
  removeComponentSupplier,
  setComponentSupplierFamilies,
  fetchBuildDescriptions,
  createBuildDescription,
  updateBuildDescription,
  deleteBuildDescription,
  fetchAddresses,
  createAddress,
  updateAddress,
  deleteAddress,
  fetchWarehouses,
  createWarehouse,
  updateWarehouse,
  deleteWarehouse,
} from "@/features/admin/services/lookup_service";
import { fetchUsers } from "@/features/admin/services/user_service";
import {
  fetchPMFamilies,
  createPMFamily,
  deletePMFamily,
  fetchFamiliesLookup,
  createFamily,
  deleteFamily,
} from "@/features/admin/services/pm_family_service";
import { useAuthStore } from "@/shared/store/useAuthStore";
import { useIsAdmin } from "@/shared/hooks/useIsAdmin";
import { stringSorter } from "@/shared/utils/tableColumnHelpers";

const { Title, Paragraph } = Typography;

export default function DBTablesManagement() {
  return (
    <Card>
      <Title level={3} style={{ marginTop: 0 }}>Database Tables</Title>
      <Paragraph type="secondary">
        Manage dictionary tables used across the system. Use caution: changes
        are immediate and may affect existing records.
      </Paragraph>
      <Tabs
        defaultActiveKey="departments"
        destroyOnHidden
        items={[
          { key: "departments", label: "Departments", children: <DepartmentsTab /> },
          { key: "forwarders", label: "Forwarders", children: <ForwardersTab /> },
          { key: "build_notes", label: "Build Notes", children: <BuildNotesTab /> },
          { key: "support_activities", label: "Support Activities", children: <SupportActivitiesTab /> },
          { key: "form_factors", label: "Form Factors", children: <FormFactorsTab /> },
          { key: "silicon_steppings", label: "Silicon Steppings", children: <SiliconSteppingsTab /> },
          { key: "components", label: "Components & Suppliers", children: <ComponentsSuppliersTab /> },
          { key: "build_descriptions", label: "Build Descriptions", children: <BuildDescriptionsTab /> },
          { key: "addresses", label: "Addresses", children: <AddressesTab /> },
          { key: "warehouses", label: "Warehouses", children: <WarehousesTab /> },
          { key: "pm_families", label: "PM \u2194 Family", children: <PMFamiliesTab /> },
        ]}
      />
    </Card>
  );
}

/* ----------------------------------------------------------------------
 * Departments
 * -------------------------------------------------------------------- */
function DepartmentsTab() {
  return (
    <SimpleCrudTab
      label="Department"
      fetcher={fetchDepartments}
      creator={createDepartment}
      updater={updateDepartment}
      remover={deleteDepartment}
      columns={[
        { title: "ID", dataIndex: "id", width: 80, sorter: (a, b) => a.id - b.id },
        { title: "Name", dataIndex: "name", sorter: stringSorter((r) => r.name) },
        {
          title: "Description",
          dataIndex: "description",
          sorter: stringSorter((r) => r.description),
          render: (v) => v || "\u2014",
        },
      ]}
      formFields={[
        { name: "name", label: "Name", required: true },
        { name: "description", label: "Description", textarea: true },
      ]}
      searchableKeys={["name", "description"]}
    />
  );
}

/* ----------------------------------------------------------------------
 * Forwarders
 * -------------------------------------------------------------------- */
function ForwardersTab() {
  return (
    <SimpleCrudTab
      label="Forwarder"
      fetcher={fetchForwarders}
      creator={createForwarder}
      updater={updateForwarder}
      remover={deleteForwarder}
      columns={[
        { title: "ID", dataIndex: "id", width: 80, sorter: (a, b) => a.id - b.id },
        { title: "Name", dataIndex: "name", sorter: stringSorter((r) => r.name) },
      ]}
      formFields={[{ name: "name", label: "Name", required: true }]}
      searchableKeys={["name"]}
    />
  );
}

/* ----------------------------------------------------------------------
 * Build Notes (with merge)
 * -------------------------------------------------------------------- */
function BuildNotesTab() {
  const [merging, setMerging] = useState(null); // primary note
  const [duplicateId, setDuplicateId] = useState(null);
  const [allNotes, setAllNotes] = useState([]);
  const [busy, setBusy] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  // Stash the current rows for the merge dialog's Select
  const trackedFetcher = async () => {
    const rows = await fetchBuildNotes();
    setAllNotes(rows || []);
    return rows;
  };

  async function handleMerge() {
    if (!merging || !duplicateId) return;
    if (duplicateId === merging.id) {
      message.error("Cannot merge a note with itself");
      return;
    }
    setBusy(true);
    try {
      const result = await mergeBuildNotes(merging.id, duplicateId);
      const moved = Object.entries(result?.transferred || {})
        .filter(([, n]) => n > 0)
        .map(([t, n]) => `${t}: ${n}`)
        .join(", ") || "no rows";
      message.success(`Merged. Repointed -> ${moved}`);
      setMerging(null);
      setDuplicateId(null);
      setReloadKey((k) => k + 1);
    } catch (e) {
      message.error(e.message || "Merge failed");
    } finally {
      setBusy(false);
    }
  }

  const mergeOptions = allNotes
    .filter((n) => merging && n.id !== merging.id)
    .map((n) => ({ value: n.id, label: `#${n.id} ${n.notes}` }));

  return (
    <>
      <SimpleCrudTab
        key={reloadKey}
        label="Build Note"
        fetcher={trackedFetcher}
        creator={createBuildNote}
        updater={updateBuildNote}
        remover={deleteBuildNote}
        columns={[
          { title: "ID", dataIndex: "id", width: 80, sorter: (a, b) => a.id - b.id },
          { title: "Note", dataIndex: "notes", sorter: stringSorter((r) => r.notes) },
        ]}
        formFields={[{ name: "notes", label: "Note", required: true, textarea: true }]}
        searchableKeys={["notes"]}
        extraActions={(row) => (
          <Button
            size="small"
            icon={<MergeCellsOutlined />}
            onClick={() => { setMerging(row); setDuplicateId(null); }}
          >
            Merge
          </Button>
        )}
      />

      <Modal
        title="Merge Duplicate Build Note"
        open={!!merging}
        onCancel={() => { setMerging(null); setDuplicateId(null); }}
        onOk={handleMerge}
        okText="Merge"
        okButtonProps={{ danger: true, disabled: !duplicateId, loading: busy }}
        destroyOnHidden
      >
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 12 }}
          message="This action is irreversible"
          description="All build plans / support activities currently linked to the duplicate note will be repointed to the primary note. The duplicate note will then be deleted."
        />
        <Form layout="vertical">
          <Form.Item label="Primary (kept)">
            <Input disabled value={merging ? `#${merging.id} ${merging.notes}` : ""} />
          </Form.Item>
          <Form.Item label="Duplicate (will be deleted)" required>
            <Select
              showSearch
              placeholder="Select duplicate note"
              value={duplicateId}
              onChange={setDuplicateId}
              options={mergeOptions}
              filterOption={(input, option) =>
                (option?.label || "").toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}

/* ----------------------------------------------------------------------
 * Support Activities
 * -------------------------------------------------------------------- */
function SupportActivitiesTab() {
  return (
    <SimpleCrudTab
      label="Support Activity"
      adminOnly
      fetcher={fetchSupportActivities}
      creator={createSupportActivity}
      updater={updateSupportActivity}
      remover={deleteSupportActivity}
      columns={[
        { title: "ID", dataIndex: "id", width: 80, sorter: (a, b) => a.id - b.id },
        { title: "Name", dataIndex: "name", sorter: stringSorter((r) => r.name) },
      ]}
      formFields={[{ name: "name", label: "Name", required: true }]}
      searchableKeys={["name"]}
    />
  );
}

function FormFactorsTab() {
  return (
    <SimpleCrudTab
      label="Form Factor"
      adminOnly
      fetcher={fetchFormFactors}
      creator={createFormFactor}
      updater={updateFormFactor}
      remover={deleteFormFactor}
      columns={[
        { title: "ID", dataIndex: "id", width: 80, sorter: (a, b) => a.id - b.id },
        { title: "Name", dataIndex: "name", sorter: stringSorter((r) => r.name) },
      ]}
      formFields={[{ name: "name", label: "Name", required: true }]}
      searchableKeys={["name"]}
    />
  );
}

function SiliconSteppingsTab() {
  return (
    <SimpleCrudTab
      label="Silicon Stepping"
      adminOnly
      fetcher={fetchSiliconSteppings}
      creator={createSiliconStepping}
      updater={updateSiliconStepping}
      remover={deleteSiliconStepping}
      columns={[
        { title: "ID", dataIndex: "id", width: 80, sorter: (a, b) => a.id - b.id },
        { title: "Name", dataIndex: "name", sorter: stringSorter((r) => r.name) },
      ]}
      formFields={[{ name: "name", label: "Name", required: true }]}
      searchableKeys={["name"]}
    />
  );
}

function ComponentsSuppliersTab() {
  const isAdmin = useIsAdmin();
  const [tree, setTree] = useState([]);
  const [allSuppliers, setAllSuppliers] = useState([]);
  const [allFamilies, setAllFamilies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");

  // Modal state
  const [compModal, setCompModal] = useState(null); // {mode:'create'|'edit', row?}
  const [compForm] = Form.useForm();
  const [supModal, setSupModal] = useState(null); // {componentId, componentName}
  const [supForm] = Form.useForm();
  const [famModal, setFamModal] = useState(null); // {componentId, supplier}
  const [famForm] = Form.useForm();
  const [supplierEditModal, setSupplierEditModal] = useState(null); // {row}
  const [supplierEditForm] = Form.useForm();
  const [createSupplierModal, setCreateSupplierModal] = useState(false);
  const [createSupplierForm] = Form.useForm();
  const [busy, setBusy] = useState(false);

  async function reload() {
    setLoading(true);
    try {
      const [t, sups, fams] = await Promise.all([
        fetchComponentSupplierTree(),
        fetchSuppliers(),
        fetchFamiliesLookup(),
      ]);
      setTree(t || []);
      setAllSuppliers(sups || []);
      setAllFamilies(fams || []);
    } catch (e) {
      message.error(e.message || "Failed to load components");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
  }, []);

  const filteredTree = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return tree;
    return tree.filter((c) => {
      if (c.name.toLowerCase().includes(q)) return true;
      return (c.suppliers || []).some(
        (s) =>
          s.name.toLowerCase().includes(q) ||
          (s.families || []).some(
            (f) =>
              f.code.toLowerCase().includes(q) ||
              f.name.toLowerCase().includes(q)
          )
      );
    });
  }, [tree, search]);

  // ---- Component CRUD handlers ----
  async function submitComponent() {
    try {
      const values = await compForm.validateFields();
      setBusy(true);
      if (compModal.mode === "create") {
        await createComponent({ name: values.name });
        message.success("Component created");
      } else {
        await updateComponent(compModal.row.id, { name: values.name });
        message.success("Component updated");
      }
      setCompModal(null);
      compForm.resetFields();
      reload();
    } catch (e) {
      if (e?.errorFields) return;
      message.error(e.message || "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteComponent(row) {
    try {
      await deleteComponent(row.id);
      message.success("Component deleted");
      reload();
    } catch (e) {
      message.error(e.message || "Delete failed");
    }
  }

  // ---- Supplier link handlers ----
  async function submitAddSupplier() {
    try {
      const values = await supForm.validateFields();
      setBusy(true);
      await addComponentSupplier(
        supModal.componentId,
        values.supplier_id,
        values.family_ids || []
      );
      message.success("Supplier linked");
      setSupModal(null);
      supForm.resetFields();
      reload();
    } catch (e) {
      if (e?.errorFields) return;
      message.error(e.message || "Failed to link supplier");
    } finally {
      setBusy(false);
    }
  }

  async function handleRemoveSupplier(componentId, supplierId) {
    try {
      await removeComponentSupplier(componentId, supplierId);
      message.success("Supplier unlinked");
      reload();
    } catch (e) {
      message.error(e.message || "Unlink failed");
    }
  }

  async function submitFamilies() {
    try {
      const values = await famForm.validateFields();
      setBusy(true);
      await setComponentSupplierFamilies(
        famModal.componentId,
        famModal.supplier.id,
        values.family_ids || []
      );
      message.success("Families updated");
      setFamModal(null);
      famForm.resetFields();
      reload();
    } catch (e) {
      if (e?.errorFields) return;
      message.error(e.message || "Save failed");
    } finally {
      setBusy(false);
    }
  }

  // ---- Supplier master CRUD (rename / delete a supplier globally) ----
  async function submitSupplierEdit() {
    try {
      const values = await supplierEditForm.validateFields();
      setBusy(true);
      await updateSupplier(supplierEditModal.row.id, { name: values.name });
      message.success("Supplier renamed");
      setSupplierEditModal(null);
      supplierEditForm.resetFields();
      reload();
    } catch (e) {
      if (e?.errorFields) return;
      message.error(e.message || "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteSupplier(row) {
    try {
      await deleteSupplier(row.id);
      message.success("Supplier deleted");
      reload();
    } catch (e) {
      message.error(e.message || "Delete failed");
    }
  }

  async function submitCreateSupplier() {
    try {
      const values = await createSupplierForm.validateFields();
      setBusy(true);
      await createSupplier({ name: values.name });
      message.success("Supplier created");
      setCreateSupplierModal(false);
      createSupplierForm.resetFields();
      reload();
    } catch (e) {
      if (e?.errorFields) return;
      message.error(e.message || "Save failed");
    } finally {
      setBusy(false);
    }
  }

  // ---- Expanded row renderer (suppliers under a component) ----
  const expandedRowRender = (component) => {
    const suppliers = component.suppliers || [];
    return (
      <div style={{ padding: "8px 12px", background: "#fafafa" }}>
        {isAdmin && (
          <Space style={{ marginBottom: 8 }}>
            <Button
              size="small"
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                supForm.resetFields();
                setSupModal({
                  componentId: component.id,
                  componentName: component.name,
                  existingSupplierIds: suppliers.map((s) => s.id),
                });
              }}
            >
              Add Supplier
            </Button>
          </Space>
        )}
        {suppliers.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="No suppliers linked"
          />
        ) : (
          <Table
            size="small"
            rowKey="id"
            pagination={false}
            dataSource={suppliers}
            columns={[
              {
                title: "Supplier",
                dataIndex: "name",
                width: 240,
                render: (v) => <b>{v}</b>,
              },
              {
                title: "Supplies for families",
                dataIndex: "families",
                render: (families) =>
                  families && families.length > 0 ? (
                    <Space size={[4, 4]} wrap>
                      {families.map((f) => (
                        <Tag key={f.id} color="blue">
                          {f.code}
                        </Tag>
                      ))}
                    </Space>
                  ) : (
                    <span style={{ color: "#999" }}>(none)</span>
                  ),
              },
              ...(isAdmin
                ? [
                    {
                      title: "Actions",
                      key: "actions",
                      width: 220,
                      render: (_, supplier) => (
                        <Space>
                          <Button
                            size="small"
                            icon={<EditOutlined />}
                            onClick={() => {
                              famForm.setFieldsValue({
                                family_ids: (supplier.families || []).map(
                                  (f) => f.id
                                ),
                              });
                              setFamModal({
                                componentId: component.id,
                                componentName: component.name,
                                supplier,
                              });
                            }}
                          >
                            Families
                          </Button>
                          <Popconfirm
                            title="Unlink this supplier from the component?"
                            description="The supplier itself is kept; only its link (and its family list for this component) is removed."
                            onConfirm={() =>
                              handleRemoveSupplier(component.id, supplier.id)
                            }
                          >
                            <Button
                              size="small"
                              danger
                              icon={<DeleteOutlined />}
                            >
                              Unlink
                            </Button>
                          </Popconfirm>
                        </Space>
                      ),
                    },
                  ]
                : []),
            ]}
          />
        )}
      </div>
    );
  };

  const supplierOptionsForAdd = useMemo(() => {
    const existing = new Set(supModal?.existingSupplierIds || []);
    return allSuppliers
      .filter((s) => !existing.has(s.id))
      .map((s) => ({ value: s.id, label: s.name }));
  }, [allSuppliers, supModal]);

  const familyOptions = useMemo(
    () =>
      allFamilies.map((f) => ({
        value: f.id,
        label: `${f.code} \u2014 ${f.name}`,
      })),
    [allFamilies]
  );

  // ---- Suppliers master list (so admins can rename/delete suppliers) ----
  const [supplierSearch, setSupplierSearch] = useState("");
  const suppliersMasterRows = useMemo(() => {
    const q = supplierSearch.trim().toLowerCase();
    if (!q) return allSuppliers;
    return allSuppliers.filter((s) =>
      (s.name || "").toLowerCase().includes(q)
    );
  }, [allSuppliers, supplierSearch]);

  return (
    <Space orientation="vertical" style={{ width: "100%" }} size={16}>
      {!isAdmin && (
        <Alert
          type="info"
          showIcon
          message="Read-only view"
          description="Only administrators may add, rename, or remove components, suppliers, or family assignments."
        />
      )}

      <Space wrap>
        <Input
          allowClear
          prefix={<SearchOutlined />}
          placeholder="Search component / supplier / family"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: 320 }}
        />
        <Button icon={<ReloadOutlined />} onClick={reload} loading={loading}>
          Reload
        </Button>
        {isAdmin && (
          <>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                compForm.resetFields();
                setCompModal({ mode: "create" });
              }}
            >
              New Component
            </Button>
            <Button
              icon={<PlusOutlined />}
              onClick={() => {
                createSupplierForm.resetFields();
                setCreateSupplierModal(true);
              }}
            >
              New Supplier
            </Button>
          </>
        )}
      </Space>

      <Table
        size="middle"
        rowKey="id"
        loading={loading}
        dataSource={filteredTree}
        pagination={{ pageSize: 20, showSizeChanger: true }}
        expandable={{
          expandedRowRender,
          rowExpandable: () => true,
        }}
        columns={[
          {
            title: "ID",
            dataIndex: "id",
            width: 80,
            sorter: (a, b) => a.id - b.id,
          },
          {
            title: "Component",
            dataIndex: "name",
            sorter: stringSorter((r) => r.name),
            render: (v) => <b>{v}</b>,
          },
          {
            title: "Suppliers",
            dataIndex: "suppliers",
            width: 140,
            render: (s) => (
              <Tag icon={<TeamOutlined />}>{(s || []).length}</Tag>
            ),
            sorter: (a, b) => (a.suppliers?.length || 0) - (b.suppliers?.length || 0),
          },
          ...(isAdmin
            ? [
                {
                  title: "Actions",
                  key: "actions",
                  width: 220,
                  render: (_, row) => (
                    <Space>
                      <Button
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => {
                          compForm.setFieldsValue({ name: row.name });
                          setCompModal({ mode: "edit", row });
                        }}
                      >
                        Rename
                      </Button>
                      <Popconfirm
                        title="Delete this component?"
                        description="This will also remove every supplier link and family assignment under it."
                        okButtonProps={{ danger: true }}
                        onConfirm={() => handleDeleteComponent(row)}
                      >
                        <Button size="small" danger icon={<DeleteOutlined />}>
                          Delete
                        </Button>
                      </Popconfirm>
                    </Space>
                  ),
                },
              ]
            : []),
        ]}
      />

      {/* Master supplier list (rename/delete suppliers globally) */}
      <Card
        size="small"
        title="All Suppliers (master list)"
        styles={{ body: { padding: 8 } }}
      >
        <Paragraph type="secondary" style={{ marginTop: 0 }}>
          Rename or delete a supplier here. Deleting a supplier also removes
          every component link and family assignment that references it.
          Sorting and filtering apply to the entire list ({allSuppliers.length}{" "}
          row{allSuppliers.length === 1 ? "" : "s"}); scroll within the table to
          reach more.
        </Paragraph>
        <Input
          allowClear
          prefix={<SearchOutlined />}
          placeholder="Filter suppliers by name"
          value={supplierSearch}
          onChange={(e) => setSupplierSearch(e.target.value)}
          style={{ width: 280, marginBottom: 8 }}
        />
        <Table
          size="small"
          rowKey="id"
          dataSource={suppliersMasterRows}
          pagination={false}
          scroll={{ y: 360 }}
          sticky
          columns={[
            {
              title: "ID",
              dataIndex: "id",
              width: 80,
              sorter: (a, b) => a.id - b.id,
            },
            {
              title: "Name",
              dataIndex: "name",
              sorter: stringSorter((r) => r.name),
            },
            ...(isAdmin
              ? [
                  {
                    title: "Actions",
                    key: "actions",
                    width: 220,
                    render: (_, row) => (
                      <Space>
                        <Button
                          size="small"
                          icon={<EditOutlined />}
                          onClick={() => {
                            supplierEditForm.setFieldsValue({ name: row.name });
                            setSupplierEditModal({ row });
                          }}
                        >
                          Rename
                        </Button>
                        <Popconfirm
                          title="Delete this supplier?"
                          description="Removes the supplier and all of its component links."
                          okButtonProps={{ danger: true }}
                          onConfirm={() => handleDeleteSupplier(row)}
                        >
                          <Button size="small" danger icon={<DeleteOutlined />}>
                            Delete
                          </Button>
                        </Popconfirm>
                      </Space>
                    ),
                  },
                ]
              : []),
          ]}
        />
      </Card>

      {/* ---- Component create/edit modal ---- */}
      <Modal
        title={compModal?.mode === "edit" ? "Rename Component" : "New Component"}
        open={!!compModal}
        onCancel={() => setCompModal(null)}
        onOk={submitComponent}
        confirmLoading={busy}
        destroyOnHidden
      >
        <Form form={compForm} layout="vertical">
          <Form.Item
            name="name"
            label="Component name"
            rules={[{ required: true, message: "Required" }]}
          >
            <Input autoFocus placeholder="e.g. ADP_PCB" />
          </Form.Item>
        </Form>
      </Modal>

      {/* ---- Add supplier modal ---- */}
      <Modal
        title={`Add supplier to ${supModal?.componentName || ""}`}
        open={!!supModal}
        onCancel={() => setSupModal(null)}
        onOk={submitAddSupplier}
        confirmLoading={busy}
        destroyOnHidden
      >
        <Form form={supForm} layout="vertical">
          <Form.Item
            name="supplier_id"
            label="Supplier"
            rules={[{ required: true, message: "Required" }]}
          >
            <Select
              showSearch
              placeholder="Pick a supplier"
              options={supplierOptionsForAdd}
              filterOption={(input, opt) =>
                (opt?.label || "").toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>
          <Form.Item
            name="family_ids"
            label="Supplies for families"
            tooltip="Optional. You can edit this later."
          >
            <Select
              mode="multiple"
              allowClear
              placeholder="Pick one or more families"
              options={familyOptions}
              filterOption={(input, opt) =>
                (opt?.label || "").toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* ---- Edit families modal ---- */}
      <Modal
        title={
          famModal
            ? `Families: ${famModal.componentName} \u2192 ${famModal.supplier.name}`
            : ""
        }
        open={!!famModal}
        onCancel={() => setFamModal(null)}
        onOk={submitFamilies}
        confirmLoading={busy}
        destroyOnHidden
      >
        <Form form={famForm} layout="vertical">
          <Form.Item name="family_ids" label="Families this supplier supplies for">
            <Select
              mode="multiple"
              allowClear
              placeholder="Pick families"
              options={familyOptions}
              filterOption={(input, opt) =>
                (opt?.label || "").toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* ---- Rename supplier modal ---- */}
      <Modal
        title="Rename Supplier"
        open={!!supplierEditModal}
        onCancel={() => setSupplierEditModal(null)}
        onOk={submitSupplierEdit}
        confirmLoading={busy}
        destroyOnHidden
      >
        <Form form={supplierEditForm} layout="vertical">
          <Form.Item
            name="name"
            label="Supplier name"
            rules={[{ required: true, message: "Required" }]}
          >
            <Input autoFocus />
          </Form.Item>
        </Form>
      </Modal>

      {/* ---- Create supplier modal ---- */}
      <Modal
        title="New Supplier"
        open={createSupplierModal}
        onCancel={() => setCreateSupplierModal(false)}
        onOk={submitCreateSupplier}
        confirmLoading={busy}
        destroyOnHidden
      >
        <Form form={createSupplierForm} layout="vertical">
          <Form.Item
            name="name"
            label="Supplier name"
            rules={[{ required: true, message: "Required" }]}
          >
            <Input autoFocus />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

function BuildDescriptionsTab() {
  const [activities, setActivities] = useState([]);
  useEffect(() => {
    fetchSupportActivities().then((rs) => setActivities(rs || [])).catch(() => {});
  }, []);
  return (
    <SimpleCrudTab
      label="Build Description"
      adminOnly
      fetcher={fetchBuildDescriptions}
      creator={createBuildDescription}
      updater={updateBuildDescription}
      remover={deleteBuildDescription}
      columns={[
        { title: "ID", dataIndex: "id", width: 80, sorter: (a, b) => a.id - b.id },
        {
          title: "Support Activity",
          dataIndex: "support_activity_name",
          sorter: stringSorter((r) => r.support_activity_name),
        },
        {
          title: "Description",
          dataIndex: "description",
          sorter: stringSorter((r) => r.description),
        },
      ]}
      formFields={[
        {
          name: "support_activity_id",
          label: "Support Activity",
          required: true,
          select: true,
          options: activities.map((a) => ({ value: a.id, label: a.name })),
        },
        { name: "description", label: "Description", required: true, textarea: true },
      ]}
      searchableKeys={["description", "support_activity_name"]}
    />
  );
}

function AddressesTab() {
  return (
    <SimpleCrudTab
      label="Address"
      fetcher={fetchAddresses}
      creator={createAddress}
      updater={updateAddress}
      remover={deleteAddress}
      columns={[
        { title: "ID", dataIndex: "id", width: 80, sorter: (a, b) => a.id - b.id },
        { title: "Label", dataIndex: "label", sorter: stringSorter((r) => r.label) },
        { title: "Line 1", dataIndex: "line1", sorter: stringSorter((r) => r.line1) },
        { title: "City", dataIndex: "city", sorter: stringSorter((r) => r.city) },
        { title: "State", dataIndex: "state", sorter: stringSorter((r) => r.state) },
        { title: "Country", dataIndex: "country", sorter: stringSorter((r) => r.country) },
        { title: "Postal Code", dataIndex: "postal_code", sorter: stringSorter((r) => r.postal_code) },
      ]}
      formFields={[
        { name: "label", label: "Label" },
        { name: "line1", label: "Line 1" },
        { name: "line2", label: "Line 2" },
        { name: "city", label: "City" },
        { name: "state", label: "State" },
        { name: "country", label: "Country" },
        { name: "postal_code", label: "Postal Code" },
        { name: "notes", label: "Notes", textarea: true },
      ]}
      searchableKeys={["label", "line1", "line2", "city", "state", "country", "postal_code"]}
    />
  );
}

function WarehousesTab() {
  return (
    <SimpleCrudTab
      label="Warehouse"
      fetcher={fetchWarehouses}
      creator={createWarehouse}
      updater={updateWarehouse}
      remover={deleteWarehouse}
      columns={[
        { title: "ID", dataIndex: "id", width: 80, sorter: (a, b) => a.id - b.id },
        { title: "Name", dataIndex: "name", sorter: stringSorter((r) => r.name) },
        { title: "Notes", dataIndex: "notes", sorter: stringSorter((r) => r.notes) },
      ]}
      formFields={[
        { name: "name", label: "Name", required: true },
        { name: "notes", label: "Notes", textarea: true },
      ]}
      searchableKeys={["name", "notes"]}
    />
  );
}

/* ----------------------------------------------------------------------
 * Reusable simple CRUD tab
 * -------------------------------------------------------------------- */
function SimpleCrudTab({
  label,
  fetcher,
  creator,
  updater,
  remover,
  columns,
  formFields,
  extraActions,
  searchableKeys,
  adminOnly = false,
  rowKey = "id",
}) {
  const isAdmin = useIsAdmin();
  const canMutate = !adminOnly || isAdmin;
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState(null);
  const [search, setSearch] = useState("");
  const [createForm] = Form.useForm();
  const [editForm] = Form.useForm();

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setRows(await fetcher());
    } catch (e) {
      setError(e.message || "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleCreate(values) {
    try {
      await creator(values);
      message.success(`${label} created`);
      setCreating(false);
      createForm.resetFields();
      load();
    } catch (e) { message.error(e.message); }
  }

  async function handleEdit(values) {
    try {
      await updater(editing.id, values);
      message.success("Updated");
      setEditing(null);
      load();
    } catch (e) { message.error(e.message); }
  }

  async function handleDelete(row) {
    try {
      await remover(row.id);
      message.success("Deleted");
      load();
    } catch (e) { message.error(e.message); }
  }

  // Client-side search across declared keys (or every column dataIndex).
  const filteredRows = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return rows;
    const keys =
      searchableKeys && searchableKeys.length
        ? searchableKeys
        : columns
            .map((c) => c.dataIndex)
            .filter((k) => typeof k === "string");
    return rows.filter((r) =>
      keys.some((k) => {
        const v = r?.[k];
        return v != null && String(v).toLowerCase().includes(term);
      }),
    );
  }, [rows, search, searchableKeys, columns]);

  const allColumns = [
    ...columns,
    {
      title: "Actions",
      key: "actions",
      width: 260,
      render: (_, r) => (
        <Space>
          {extraActions ? extraActions(r, load) : null}
          <Tooltip title={canMutate ? "" : "Admins only"}>
            <Button
              size="small"
              icon={<EditOutlined />}
              disabled={!canMutate}
              onClick={() => { setEditing(r); editForm.setFieldsValue(r); }}
            >
              Edit
            </Button>
          </Tooltip>
          <Tooltip title={canMutate ? "" : "Admins only"}>
            <Popconfirm
              title={`Delete ${label.toLowerCase()}?`}
              onConfirm={() => handleDelete(r)}
              okButtonProps={{ danger: true }}
              disabled={!canMutate}
            >
              <Button
                size="small"
                danger
                icon={<DeleteOutlined />}
                disabled={!canMutate}
              >
                Delete
              </Button>
            </Popconfirm>
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <>
      {adminOnly && !isAdmin && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message="Read-only"
          description={`Only administrators can create, edit, or delete ${label.toLowerCase()}s.`}
        />
      )}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: 12,
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        <Input
          allowClear
          prefix={<SearchOutlined />}
          placeholder={`Search ${label.toLowerCase()}\u2026`}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ maxWidth: 320 }}
        />
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load}>Refresh</Button>
          <Tooltip title={canMutate ? "" : "Admins only"}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => setCreating(true)}
              disabled={!canMutate}
            >
              New {label}
            </Button>
          </Tooltip>
        </Space>
      </div>
      {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 12 }} />}
      <Table
        rowKey={rowKey}
        columns={allColumns}
        dataSource={filteredRows}
        loading={loading}
        pagination={{ pageSize: 20, showSizeChanger: true }}
      />

      <Modal title={`Create ${label}`} open={creating} onCancel={() => setCreating(false)} onOk={() => createForm.submit()} destroyOnHidden>
        <Form form={createForm} layout="vertical" onFinish={handleCreate}>
          {formFields.map(renderField)}
        </Form>
      </Modal>
      <Modal title={`Edit ${label}`} open={!!editing} onCancel={() => setEditing(null)} onOk={() => editForm.submit()} destroyOnHidden>
        <Form form={editForm} layout="vertical" onFinish={handleEdit}>
          {formFields.map(renderField)}
        </Form>
      </Modal>
    </>
  );
}

function renderField(f) {
  let input;
  if (f.select) {
    input = (
      <Select
        showSearch
        allowClear
        options={f.options || []}
        filterOption={(input, option) =>
          (option?.label || "").toLowerCase().includes(input.toLowerCase())
        }
      />
    );
  } else if (f.textarea) {
    input = <Input.TextArea rows={3} />;
  } else {
    input = <Input />;
  }
  return (
    <Form.Item
      key={f.name}
      name={f.name}
      label={f.label}
      rules={f.required ? [{ required: true, message: `${f.label} is required` }] : []}
    >
      {input}
    </Form.Item>
  );
}

/* ----------------------------------------------------------------------
 * PM ↔ Family (admin-only edits) — card per family
 * -------------------------------------------------------------------- */
function PMFamiliesTab() {
  const authUser = useAuthStore((s) => s.user);
  const role =
    authUser?.role ||
    (Array.isArray(authUser?.roles) ? authUser.roles[0] : null) ||
    null;
  const isAdmin = role === "Admin";

  const [rows, setRows] = useState([]);
  const [users, setUsers] = useState([]);
  const [families, setFamilies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [creatingFamily, setCreatingFamily] = useState(null); // family obj or null
  const [creatingNewFamily, setCreatingNewFamily] = useState(false);
  const [createForm] = Form.useForm();
  const [newFamilyForm] = Form.useForm();

  async function handleCreateFamily(values) {
    try {
      await createFamily(values);
      message.success(`Family ${values.code} created`);
      setCreatingNewFamily(false);
      newFamilyForm.resetFields();
      load();
    } catch (e) {
      message.error(e.message);
    }
  }

  async function load() {
    setLoading(true);
    try {
      const [pf, fams, usrs] = await Promise.all([
        fetchPMFamilies(),
        fetchFamiliesLookup(),
        fetchUsers({ page_size: 500 }).catch(() => []),
      ]);
      setRows(pf || []);
      setFamilies(fams || []);
      setUsers(usrs?.items || usrs || []);
    } catch (e) {
      message.error(e.message || "Failed to load PM-Family assignments");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(values) {
    try {
      await createPMFamily({
        family_id: creatingFamily.id,
        user_id: values.user_id,
      });
      message.success("PM assigned");
      setCreatingFamily(null);
      createForm.resetFields();
      load();
    } catch (e) {
      message.error(e.message);
    }
  }

  async function handleDelete(assignment) {
    try {
      await deletePMFamily(assignment.id);
      message.success("PM removed");
      load();
    } catch (e) {
      message.error(e.message);
    }
  }

  async function handleDeleteFamily(family) {
    try {
      await deleteFamily(family.id);
      message.success(`Family ${family.code} deleted`);
      load();
    } catch (e) {
      message.error(e.message || "Failed to delete family");
    }
  }

  // Group assignments by family_id.
  const assignmentsByFamily = rows.reduce((acc, r) => {
    const fid = r.family?.id;
    if (fid == null) return acc;
    (acc[fid] = acc[fid] || []).push(r);
    return acc;
  }, {});

  const term = search.trim().toLowerCase();
  const visibleFamilies = families.filter((f) => {
    if (!term) return true;
    return (
      f.code?.toLowerCase().includes(term) ||
      f.name?.toLowerCase().includes(term)
    );
  });

  // For the assign modal: only users not already assigned to this family.
  const assignedUserIds = creatingFamily
    ? new Set(
        (assignmentsByFamily[creatingFamily.id] || []).map((a) => a.user?.id)
      )
    : new Set();

  const userOptions = users
    .filter((u) => !assignedUserIds.has(u.id))
    .map((u) => ({
      value: u.id,
      label: u.full_name
        ? `${u.full_name}${u.email ? ` <${u.email}>` : ""}`
        : u.email || `User #${u.id}`,
    }));

  return (
    <>
      {!isAdmin && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12 }}
          message="Read-only"
          description="Only administrators can add or remove PM-Family assignments."
        />
      )}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 12,
          gap: 8,
          flexWrap: "wrap",
        }}
      >
        <Input.Search
          placeholder="Filter families by code or name"
          allowClear
          onChange={(e) => setSearch(e.target.value)}
          style={{ maxWidth: 320 }}
        />
        <Space>
          <Button icon={<ReloadOutlined />} onClick={load} loading={loading}>
            Refresh
          </Button>
          <Tooltip title={isAdmin ? "Create a new family" : "Admins only"}>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              disabled={!isAdmin}
              onClick={() => {
                newFamilyForm.resetFields();
                setCreatingNewFamily(true);
              }}
            >
              + Family
            </Button>
          </Tooltip>
        </Space>
      </div>

      {visibleFamilies.length === 0 ? (
        <Empty description="No families found" />
      ) : (
        <Row gutter={[12, 12]}>
          {visibleFamilies.map((f) => {
            const pms = assignmentsByFamily[f.id] || [];
            return (
              <Col key={f.id} xs={24} sm={12} md={8} xl={6}>
                <Card
                  size="small"
                  title={
                    <Space size={6}>
                      <Tag color="blue" style={{ marginRight: 0 }}>
                        {f.code}
                      </Tag>
                      <span>{f.name}</span>
                    </Space>
                  }
                  extra={
                    <Space size={4}>
                      <Tooltip
                        title={
                          isAdmin
                            ? "Assign a PM to this family"
                            : "Admins only"
                        }
                      >
                        <Button
                          size="small"
                          type="primary"
                          icon={<PlusOutlined />}
                          disabled={!isAdmin}
                          onClick={() => {
                            createForm.resetFields();
                            setCreatingFamily(f);
                          }}
                        >
                          PM
                        </Button>
                      </Tooltip>
                      <Popconfirm
                        title={`Delete family ${f.code}?`}
                        description="This also removes its PM assignments and form-factor mappings. Families referenced by existing build requests cannot be deleted."
                        okButtonProps={{ danger: true }}
                        okText="Delete"
                        disabled={!isAdmin}
                        onConfirm={() => handleDeleteFamily(f)}
                      >
                        <Tooltip
                          title={isAdmin ? "Delete this family" : "Admins only"}
                        >
                          <Button
                            size="small"
                            danger
                            icon={<DeleteOutlined />}
                            disabled={!isAdmin}
                          />
                        </Tooltip>
                      </Popconfirm>
                    </Space>
                  }
                  styles={{ body: { minHeight: 96 } }}
                >
                  {pms.length === 0 ? (
                    <Typography.Text type="secondary">
                      No PMs assigned
                    </Typography.Text>
                  ) : (
                    <Space size={[6, 6]} wrap>
                      {pms.map((a) => {
                        const label =
                          a.user?.full_name ||
                          a.user?.email ||
                          `User #${a.user?.id ?? "—"}`;
                        const tag = (
                          <Tag
                            color="geekblue"
                            closable={isAdmin}
                            onClose={(e) => {
                              e.preventDefault();
                            }}
                            style={{ marginInlineEnd: 0 }}
                          >
                            <Tooltip title={a.user?.email || ""}>
                              {label}
                            </Tooltip>
                          </Tag>
                        );
                        if (!isAdmin) {
                          return (
                            <span key={a.id}>{tag}</span>
                          );
                        }
                        return (
                          <Popconfirm
                            key={a.id}
                            title={`Remove ${label} from ${f.code}?`}
                            okButtonProps={{ danger: true }}
                            onConfirm={() => handleDelete(a)}
                          >
                            {tag}
                          </Popconfirm>
                        );
                      })}
                    </Space>
                  )}
                </Card>
              </Col>
            );
          })}
        </Row>
      )}

      <Modal
        title={
          creatingFamily
            ? `Assign PM to ${creatingFamily.code} — ${creatingFamily.name}`
            : "Assign PM"
        }
        open={!!creatingFamily}
        onCancel={() => setCreatingFamily(null)}
        onOk={() => createForm.submit()}
        destroyOnHidden
      >
        <Form form={createForm} layout="vertical" onFinish={handleCreate}>
          <Form.Item
            name="user_id"
            label="PM (User)"
            rules={[{ required: true, message: "Select a user" }]}
          >
            <Select
              showSearch
              placeholder="Select a user"
              options={userOptions}
              filterOption={(input, option) =>
                (option?.label || "")
                  .toLowerCase()
                  .includes(input.toLowerCase())
              }
              notFoundContent={
                userOptions.length === 0
                  ? "All known users are already assigned"
                  : null
              }
            />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Create New Family"
        open={creatingNewFamily}
        onCancel={() => setCreatingNewFamily(false)}
        onOk={() => newFamilyForm.submit()}
        destroyOnHidden
      >
        <Form
          form={newFamilyForm}
          layout="vertical"
          onFinish={handleCreateFamily}
        >
          <Form.Item
            name="code"
            label="Code"
            rules={[{ required: true, message: "Code is required" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="name"
            label="Name"
            rules={[{ required: true, message: "Name is required" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
