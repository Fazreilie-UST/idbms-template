import { useMemo, useState } from "react";
import { useIsAdmin } from "@/shared/hooks/useIsAdmin";
import { useLocation, useNavigate } from "react-router-dom";
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
  ReadOutlined,
} from "@ant-design/icons";


// Place these above Sidebar function
const sharedTrackerGroup = {
  key: "trackers-group",
  icon: <SearchOutlined />,
  label: "Trackers",
  children: [
    { key: "/build-plan-tracker", icon: <OrderedListOutlined />, label: "Build Plan" },
    { key: "/build-request-tracker", icon: <OrderedListOutlined />, label: "Build Request" },
    { key: "/shipment-tracker", icon: <TruckOutlined />, label: "Shipment" },
  ],
};


const documentationItem = {
  key: "/documentation",
  icon: <ReadOutlined />,
  label: "Documentation",
};

const reportIssueItem = {
  key: "/logs/reports",
  icon: <BookOutlined />,
  label: "Report an Issue",
};

  export default function Sidebar({ isProgramManager, isRequestor, role }) {
    const isAdmin = useIsAdmin();
    const { Sider } = Layout;
    const location = useLocation();
    const navigate = useNavigate();
    const [collapsed, setCollapsed] = useState(false);

<<<<<<< Updated upstream
    const documentationItem = {
      key: "/documentation",
      icon: <ReadOutlined />,
      label: "Documentation",
    };

    const pmItems: MenuItems = [
=======


    const auditLogsGroup = isAdmin
      ? {
          key: "audit-logs-group",
          icon: <SearchOutlined />,
          label: "Audit & Logs",
          children: [
            { key: "/logs/audit", icon: <OrderedListOutlined />, label: "Audit Logs" },
            { key: "/logs/bug-reports", icon: <BookOutlined />, label: "Bug Reports" },
          ],
        }
      : null;

    const pmItems = [
>>>>>>> Stashed changes
      { key: "/pm/dashboard", icon: <DashboardOutlined />, label: "Dashboard" },
      { key: "/pm/build-plans", icon: <BookOutlined />, label: "My Build Plans" },
      { key: "/pm/build-requests", icon: <SolutionOutlined />, label: "Manage Build Requests" },
      sharedTrackerGroup,
      {
        key: "administration-group",
        icon: <SettingOutlined />,
        label: "Administration",
        children: [
          { key: "/pm/admin/import-build-plan", icon: <CloudUploadOutlined />, label: "Import Build Plan" },
          { key: "/pm/admin/import-shipments", icon: <CloudUploadOutlined />, label: "Import Shipments" },
          { key: "/pm/admin/users", icon: <UserOutlined />, label: "User Management" },
          { key: "/pm/admin/roles", icon: <SafetyCertificateOutlined />, label: "Role Management" },
          { key: "/pm/admin/db-tables", icon: <DatabaseOutlined />, label: "DB Tables" },
        ],
      },
      documentationItem,
      ...(auditLogsGroup ? [auditLogsGroup] : []),
      reportIssueItem,
    ];

    const requestorItems = [
      { key: "/requestor/dashboard", icon: <DashboardOutlined />, label: "Dashboard" },
      { key: "/requestor/build-requests", icon: <SolutionOutlined />, label: "My Build Requests" },
      sharedTrackerGroup,
<<<<<<< Updated upstream
      documentationItem,
    ];

    if (isProgramManager) {
      pmItems.push(documentationItem);
    }

    return [
      ...(isProgramManager ? pmItems : []),
      ...(isRequestor && !isProgramManager ? requestorItems : []),
    ];
  }, [isProgramManager, isRequestor]);
=======
      ...(auditLogsGroup ? [auditLogsGroup] : []),
      documentationItem,
      reportIssueItem,
    ];

    const items = useMemo(() => {
      return [
        ...(isProgramManager ? pmItems : []),
        ...(isRequestor && !isProgramManager ? requestorItems : []),
      ];
    }, [isProgramManager, isRequestor, role]);
>>>>>>> Stashed changes

    const selectedKey = useMemo(() => {
      if (location.pathname.startsWith("/pm/build-plans/")) return "/pm/build-plans";
      if (location.pathname.startsWith("/pm/build-requests/")) return "/pm/build-requests";
      if (location.pathname.startsWith("/pm/shippings/")) return "/pm/shippings";
      if (location.pathname.startsWith("/requestor/build-requests/")) return "/requestor/build-requests";
      if (location.pathname.startsWith("/build-plan-tracker/")) return "/build-plan-tracker";
      if (location.pathname.startsWith("/build-request-tracker/")) return "/build-request-tracker";
      if (location.pathname.startsWith("/shipment-tracker/")) return "/shipment-tracker";
      return location.pathname;
    }, [location.pathname]);

    const handleMenuClick = ({ key }) => {
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

