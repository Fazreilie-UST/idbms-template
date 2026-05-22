import { useMemo, useState } from "react";
import { Layout, Menu, Button } from "antd";
import type { MenuProps } from "antd";
import {
  DashboardOutlined,
  DatabaseOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  OrderedListOutlined,
  TruckOutlined,
  SearchOutlined,
  BookOutlined,
  SolutionOutlined,
  SettingOutlined,
  CloudUploadOutlined,
  UserOutlined,
  SafetyCertificateOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/shared/store/useAuthStore";

const { Sider } = Layout;

type MenuItems = NonNullable<MenuProps["items"]>;

const getStoredRole = (): string | null => {
  try {
    return localStorage.getItem("role") || localStorage.getItem("user_role");
  } catch {
    return null;
  }
};

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const user = useAuthStore((state) => state.user);

  const role = user?.role ?? getStoredRole();
  // Admin sees the same nav as a Program Manager.
  const isProgramManager =
    role === "Program Manager" ||
    role === "Admin" ||
    location.pathname.startsWith("/pm");
  const isRequestor =
    role === "Requestor" || location.pathname.startsWith("/requestor");

  const items = useMemo<MenuItems>(() => {
    const sharedTrackerGroup = {
      key: "trackers-group",
      icon: <SearchOutlined />,
      label: "Trackers",
      children: [
        {
          key: "/build-plan-tracker",
          icon: <OrderedListOutlined />,
          label: "Build Plan",
        },
        {
          key: "/build-request-tracker",
          icon: <OrderedListOutlined />,
          label: "Build Request",
        },
        {
          key: "/shipment-tracker",
          icon: <TruckOutlined />,
          label: "Shipment",
        },
      ],
    };

    const pmItems: MenuItems = [
      { key: "/pm/dashboard", icon: <DashboardOutlined />, label: "Dashboard" },
      { key: "/pm/build-plans", icon: <BookOutlined />, label: "My Build Plans" },
      {
        key: "/pm/build-requests",
        icon: <SolutionOutlined />,
        label: "Manage Build Requests",
      },
      sharedTrackerGroup,
      {
        key: "administration-group",
        icon: <SettingOutlined />,
        label: "Administration",
        children: [
          {
            key: "/pm/admin/import-build-plan",
            icon: <CloudUploadOutlined />,
            label: "Import Build Plan",
          },
          {
            key: "/pm/admin/import-shipments",
            icon: <CloudUploadOutlined />,
            label: "Import Shipments",
          },
          {
            key: "/pm/admin/users",
            icon: <UserOutlined />,
            label: "User Management",
          },
          {
            key: "/pm/admin/roles",
            icon: <SafetyCertificateOutlined />,
            label: "Role Management",
          },
          {
            key: "/pm/admin/db-tables",
            icon: <DatabaseOutlined />,
            label: "DB Tables",
          },
        ],
      },
    ];

    const requestorItems: MenuItems = [
      {
        key: "/requestor/dashboard",
        icon: <DashboardOutlined />,
        label: "Dashboard",
      },
      {
        key: "/requestor/build-requests",
        icon: <SolutionOutlined />,
        label: "My Build Requests",
      },
      sharedTrackerGroup,
    ];

    return [
      ...(isProgramManager ? pmItems : []),
      ...(isRequestor && !isProgramManager ? requestorItems : []),
    ];
  }, [isProgramManager, isRequestor]);

  const selectedKey = useMemo(() => {
    if (location.pathname.startsWith("/pm/build-plans/")) return "/pm/build-plans";
    if (location.pathname.startsWith("/pm/build-requests/")) return "/pm/build-requests";
    if (location.pathname.startsWith("/pm/shippings/")) return "/pm/shippings";
    if (location.pathname.startsWith("/requestor/build-requests/"))
      return "/requestor/build-requests";
    if (location.pathname.startsWith("/build-plan-tracker/"))
      return "/build-plan-tracker";
    if (location.pathname.startsWith("/build-request-tracker/"))
      return "/build-request-tracker";
    if (location.pathname.startsWith("/shipment-tracker/"))
      return "/shipment-tracker";
    return location.pathname;
  }, [location.pathname]);

  const handleMenuClick: NonNullable<MenuProps["onClick"]> = ({ key }) => {
    if (typeof key === "string" && key.startsWith("/")) {
      navigate(key);
    }
  };

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      width="fit-content"
      trigger={null}
      style={{ minHeight: "100vh" }}
    >
      <div
        style={{
          height: 64,
          color: "white",
          display: "flex",
          alignItems: "center",
          justifyContent: collapsed ? "center" : "space-between",
          padding: "0 16px",
          fontWeight: "bold",
          fontSize: 16,
        }}
      >
        {!collapsed && <span>NPI DBMS</span>}
        <Button
          type="text"
          onClick={() => setCollapsed(!collapsed)}
          style={{ color: "white" }}
          icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        />
      </div>

      <Menu
        theme="dark"
        mode="inline"
        selectedKeys={[selectedKey]}
        defaultOpenKeys={[
          "pm-build-plans-group",
          "pm-build-requests-group",
          "pm-shipments-group",
          "stocks-group",
          "administration-group",
        ]}
        items={items}
        onClick={handleMenuClick}
      />
    </Sider>
  );
}
