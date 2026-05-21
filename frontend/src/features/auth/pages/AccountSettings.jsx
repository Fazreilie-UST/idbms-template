import { useMemo, useState } from "react";
import {
  Card,
  Descriptions,
  Tabs,
  Avatar,
  Typography,
  Space,
  Tag,
  Empty,
  Upload,
  Button,
  Popconfirm,
  message,
  theme,
} from "antd";
import {
  UserOutlined,
  SettingOutlined,
  UploadOutlined,
  DeleteOutlined,
} from "@ant-design/icons";
import { useSearchParams } from "react-router-dom";
import { useAuthStore } from "@/shared/store/useAuthStore";
import { resolveBackendUrl } from "@/config";
import {
  uploadAvatar,
  deleteAvatar,
} from "@/features/auth/services/auth_service";

const { Title, Text } = Typography;

const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"];
const MAX_AVATAR_MB = 2;

export default function AccountSettings() {
  const user = useAuthStore((state) => state.user);
  const setUser = useAuthStore((state) => state.setUser);
  const [searchParams, setSearchParams] = useSearchParams();
  const activeTab = searchParams.get("tab") === "settings" ? "settings" : "profile";
  const { token } = theme.useToken();

  const [uploading, setUploading] = useState(false);
  const [removing, setRemoving] = useState(false);

  const displayName = useMemo(
    () => user?.full_name || user?.email || "Unknown user",
    [user],
  );

  const avatarUrl = useMemo(
    () => resolveBackendUrl(user?.profile_picture_url ?? null),
    [user?.profile_picture_url],
  );

  const defaultAvatarStyle = { backgroundColor: token.colorPrimary };

  const persistUser = (updated) => {
    const merged = { ...(user || {}), ...updated };
    setUser(merged);
    try {
      localStorage.setItem("user", JSON.stringify(merged));
    } catch {
      /* ignore storage errors */
    }
  };

  const onTabChange = (key) => {
    const next = new URLSearchParams(searchParams);
    if (key === "profile") {
      next.delete("tab");
    } else {
      next.set("tab", key);
    }
    setSearchParams(next, { replace: true });
  };

  const beforeUpload = (file) => {
    if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) {
      message.error("Please upload a JPEG, PNG, WebP, or GIF image.");
      return Upload.LIST_IGNORE;
    }
    if (file.size > MAX_AVATAR_MB * 1024 * 1024) {
      message.error(`Image must be smaller than ${MAX_AVATAR_MB} MB.`);
      return Upload.LIST_IGNORE;
    }
    return true;
  };

  const customRequest = async ({ file, onSuccess, onError }) => {
    setUploading(true);
    try {
      const updated = await uploadAvatar(file);
      persistUser(updated);
      message.success("Profile picture updated.");
      onSuccess?.(updated, file);
    } catch (err) {
      message.error(err?.message || "Failed to upload picture.");
      onError?.(err);
    } finally {
      setUploading(false);
    }
  };

  const handleRemove = async () => {
    setRemoving(true);
    try {
      const updated = await deleteAvatar();
      persistUser(updated);
      message.success("Profile picture removed.");
    } catch (err) {
      message.error(err?.message || "Failed to remove picture.");
    } finally {
      setRemoving(false);
    }
  };

  if (!user) {
    return (
      <Card>
        <Empty description="No user information available." />
      </Card>
    );
  }

  return (
    <div>
      <Space align="center" style={{ marginBottom: 24 }} size="large">
        <Avatar
          size={64}
          src={avatarUrl || undefined}
          icon={<UserOutlined />}
          style={avatarUrl ? undefined : defaultAvatarStyle}
        />
        <div>
          <Title level={3} style={{ margin: 0 }}>
            {displayName}
          </Title>
          <Text type="secondary">{user.email}</Text>
        </div>
      </Space>

      <Tabs
        activeKey={activeTab}
        onChange={onTabChange}
        items={[
          {
            key: "profile",
            label: (
              <span>
                <UserOutlined /> Profile
              </span>
            ),
            children: (
              <Card>
                <Space
                  orientation="vertical"
                  size="large"
                  style={{ width: "100%" }}
                >
                  <Space align="center" size="large" wrap>
                    <Avatar
                      size={96}
                      src={avatarUrl || undefined}
                      icon={<UserOutlined />}
                      style={avatarUrl ? undefined : defaultAvatarStyle}
                    />
                    <Space orientation="vertical" size="small">
                      <Text strong>Profile picture</Text>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        JPEG, PNG, WebP, or GIF · up to {MAX_AVATAR_MB} MB
                      </Text>
                      <Space>
                        <Upload
                          accept={ACCEPTED_IMAGE_TYPES.join(",")}
                          showUploadList={false}
                          beforeUpload={beforeUpload}
                          customRequest={customRequest}
                          disabled={uploading || removing}
                        >
                          <Button
                            icon={<UploadOutlined />}
                            loading={uploading}
                            disabled={removing}
                          >
                            {avatarUrl ? "Change picture" : "Upload picture"}
                          </Button>
                        </Upload>
                        {avatarUrl && (
                          <Popconfirm
                            title="Remove profile picture?"
                            okText="Remove"
                            cancelText="Cancel"
                            onConfirm={handleRemove}
                            disabled={uploading || removing}
                          >
                            <Button
                              danger
                              icon={<DeleteOutlined />}
                              loading={removing}
                              disabled={uploading}
                            >
                              Remove
                            </Button>
                          </Popconfirm>
                        )}
                      </Space>
                    </Space>
                  </Space>

                  <Descriptions column={1} bordered size="middle">
                    <Descriptions.Item label="Full Name">
                      {user.full_name || "-"}
                    </Descriptions.Item>
                    <Descriptions.Item label="Email">
                      {user.email || "-"}
                    </Descriptions.Item>
                    <Descriptions.Item label="Role">
                      {user.role
                        ? <Tag color="blue">{typeof user.role === "string" ? user.role : user.role.role_name}</Tag>
                        : "-"}
                    </Descriptions.Item>
                    {Array.isArray(user.roles) && user.roles.length > 0 && (
                      <Descriptions.Item label="All Roles">
                        <Space wrap>
                          {user.roles.map((r) => {
                            const name = typeof r === "string" ? r : r.role_name;
                            const id = typeof r === "string" ? r : r.id ?? name;
                            return <Tag key={id}>{name}</Tag>;
                          })}
                        </Space>
                      </Descriptions.Item>
                    )}
                    {user.id !== undefined && (
                      <Descriptions.Item label="User ID">{user.id}</Descriptions.Item>
                    )}
                  </Descriptions>
                </Space>
              </Card>
            ),
          },
          {
            key: "settings",
            label: (
              <span>
                <SettingOutlined /> Settings
              </span>
            ),
            children: (
              <Card>
                <Empty description="No settings available yet." />
              </Card>
            ),
          },
        ]}
      />
    </div>
  );
}
