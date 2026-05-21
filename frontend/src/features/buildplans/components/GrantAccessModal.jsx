import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Divider,
  List,
  Modal,
  Radio,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
} from "antd";
import { fetchUsers } from "@/features/admin/services/user_service";
import {
  fetchBuildPlanAccess,
  grantBuildPlanAccess,
} from "@/features/buildplans/services/build_plan_service";

const { Text } = Typography;

function userLabel(u) {
  return `${u.full_name || `User #${u.id}`}${u.email ? ` (${u.email})` : ""}`;
}

export default function GrantAccessModal({
  open,
  onClose,
  buildPlanIds,
  onGranted,
}) {
  const singlePlanId = buildPlanIds.length === 1 ? buildPlanIds[0] : null;

  const [userOptions, setUserOptions] = useState([]);
  const [userSearch, setUserSearch] = useState("");
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [selectedUserIds, setSelectedUserIds] = useState([]);
  const [accessType, setAccessType] = useState("editor");
  const [scope, setScope] = useState("plan");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const [accessList, setAccessList] = useState(null);
  const [loadingAccess, setLoadingAccess] = useState(false);

  // Reset on close.
  useEffect(() => {
    if (!open) {
      setSelectedUserIds([]);
      setAccessType("editor");
      setScope("plan");
      setUserSearch("");
      setError(null);
      setAccessList(null);
    }
  }, [open]);

  // Fetch current access entries (only when viewing a single plan).
  useEffect(() => {
    if (!open || !singlePlanId) return;
    let cancelled = false;
    setLoadingAccess(true);
    fetchBuildPlanAccess(singlePlanId)
      .then((data) => !cancelled && setAccessList(data))
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoadingAccess(false));
    return () => {
      cancelled = true;
    };
  }, [open, singlePlanId]);

  // Fetch PMs for the picker.
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoadingUsers(true);
    fetchUsers({
      limit: 50,
      role: "Program Manager",
      is_active: true,
      ...(userSearch ? { search: userSearch } : {}),
    })
      .then((users) => {
        if (cancelled) return;
        setUserOptions(
          (users || []).map((u) => ({
            value: u.id,
            label: userLabel(u),
          })),
        );
      })
      .catch((e) => !cancelled && setError(e.message))
      .finally(() => !cancelled && setLoadingUsers(false));
    return () => {
      cancelled = true;
    };
  }, [open, userSearch]);

  // For multi-select, only allow management if backend says so for *every*
  // selected plan. We only fetch one (the single plan case). For multi-plan
  // grants from the table, fall back to letting the request fail with 403.
  const canManage = singlePlanId ? accessList?.can_manage !== false : true;

  const disabled = useMemo(
    () =>
      submitting ||
      selectedUserIds.length === 0 ||
      buildPlanIds.length === 0 ||
      !canManage,
    [submitting, selectedUserIds, buildPlanIds, canManage],
  );

  async function handleOk() {
    setSubmitting(true);
    setError(null);
    try {
      const result = await grantBuildPlanAccess({
        build_plan_ids: buildPlanIds,
        user_ids: selectedUserIds,
        access_type: accessType,
        scope,
      });
      onGranted?.(result);
      onClose();
    } catch (e) {
      setError(e.message || "Failed to grant access");
    } finally {
      setSubmitting(false);
    }
  }

  const entries = accessList?.entries || [];

  return (
    <Modal
      title="Build plan access"
      open={open}
      onCancel={onClose}
      onOk={handleOk}
      okText="Grant"
      okButtonProps={{ disabled, loading: submitting }}
      destroyOnClose
      width={560}
    >
      <Space orientation="vertical" size="middle" style={{ width: "100%" }}>
        {singlePlanId && (
          <div>
            <Text strong>Current access</Text>
            <div style={{ marginTop: 4 }}>
              {loadingAccess ? (
                <Spin size="small" />
              ) : entries.length === 0 ? (
                <Text type="secondary">
                  No explicit access — only implicit viewers.
                </Text>
              ) : (
                <List
                  size="small"
                  bordered
                  dataSource={entries}
                  renderItem={(entry) => (
                    <List.Item>
                      <Space size={8} wrap>
                        <Text>{userLabel(entry.user)}</Text>
                        <Tag color={entry.access_type === "owner" ? "gold" : "blue"}>
                          {entry.access_type}
                        </Tag>
                        <Tag>
                          {entry.scope === "family" ? "family/SKU" : "this plan"}
                        </Tag>
                      </Space>
                    </List.Item>
                  )}
                />
              )}
            </div>
          </div>
        )}

        {!canManage && (
          <Alert
            type="warning"
            showIcon
            message="You don't have permission to grant access on this build plan"
            description="Only an admin or an owner of the plan can manage access."
          />
        )}

        <Divider style={{ margin: 0 }}>Grant new access</Divider>

        <Text type="secondary">
          Granting access on {buildPlanIds.length} selected build plan
          {buildPlanIds.length === 1 ? "" : "s"}.
        </Text>

        <div>
          <Text strong>Scope</Text>
          <div style={{ marginTop: 4 }}>
            <Radio.Group
              value={scope}
              onChange={(e) => setScope(e.target.value)}
              disabled={!canManage}
            >
              <Radio value="plan">These build plans only</Radio>
              <Radio value="family">
                Entire family / SKU (covers all plans sharing the family-SKU)
              </Radio>
            </Radio.Group>
          </div>
        </div>

        <div>
          <Text strong>Program Managers</Text>
          <Select
            mode="multiple"
            showSearch
            allowClear
            filterOption={false}
            placeholder="Search by name, email, or employee ID"
            value={selectedUserIds}
            onChange={setSelectedUserIds}
            onSearch={setUserSearch}
            loading={loadingUsers}
            options={userOptions}
            disabled={!canManage}
            style={{ width: "100%", marginTop: 4 }}
          />
        </div>

        <div>
          <Text strong>Access type</Text>
          <div style={{ marginTop: 4 }}>
            <Radio.Group
              value={accessType}
              onChange={(e) => setAccessType(e.target.value)}
              disabled={!canManage}
            >
              <Radio value="editor">Editor</Radio>
              <Radio value="owner">Owner</Radio>
            </Radio.Group>
          </div>
        </div>

        {error && <Alert type="error" showIcon message={error} />}
      </Space>
    </Modal>
  );
}
