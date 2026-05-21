import { Layout, Dropdown, Avatar, Space, Typography, theme } from "antd";
import type { MenuProps } from "antd";
import {
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
  DownOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/shared/store/useAuthStore";
import { API, resolveBackendUrl } from "@/config";
import { authHeaders } from "@/shared/services/helper";

const { Header } = Layout;
const { Text } = Typography;

export default function AppHeader() {
  const navigate = useNavigate();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const { token } = theme.useToken();

  const displayName =
    (user?.full_name as string) ||
    (user?.email as string) ||
    "Account";

  const avatarSrc = resolveBackendUrl(
    (user?.profile_picture_url as string | null | undefined) ?? null,
  );

  const handleLogout = () => {
    fetch(`${API}/auth/logout`, {
      method: "POST",
      headers: authHeaders(),
      credentials: "include",
    }).catch(() => {});
    logout();
    navigate("/", { replace: true });
  };

  const items: MenuProps["items"] = [
    {
      key: "profile",
      icon: <UserOutlined />,
      label: "Account",
      onClick: () => navigate("/account"),
    },
    {
      key: "settings",
      icon: <SettingOutlined />,
      label: "Settings",
      onClick: () => navigate("/account?tab=settings"),
    },
    { type: "divider" },
    {
      key: "logout",
      icon: <LogoutOutlined />,
      label: "Logout",
      danger: true,
      onClick: handleLogout,
    },
  ];

  return (
    <Header
      style={{
        background: token.colorBgContainer,
        padding: "0 24px",
        display: "flex",
        justifyContent: "flex-end",
        alignItems: "center",
        borderBottom: `1px solid ${token.colorBorderSecondary}`,
        height: 56,
        lineHeight: "56px",
      }}
    >
      <Dropdown menu={{ items }} placement="bottomRight" trigger={["click"]}>
        <Space style={{ cursor: "pointer" }}>
          <Text strong>{displayName}</Text>
          <Avatar
            size="small"
            src={avatarSrc || undefined}
            icon={<UserOutlined />}
            style={avatarSrc ? undefined : { backgroundColor: token.colorPrimary }}
          />
          <DownOutlined style={{ fontSize: 10, color: token.colorTextTertiary }} />
        </Space>
      </Dropdown>
    </Header>
  );
}
