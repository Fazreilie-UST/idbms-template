import { useState } from "react";
import { Layout, Menu, Button } from "antd";
import {
  DashboardOutlined,
  DatabaseOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from "@ant-design/icons";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuthStore } from "../../store/useAuthStore";

const { Sider } = Layout;

export default function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const setToken = useAuthStore((state) => state.setToken);

  const items = [
    {
      key: "/dashboard",
      icon: <DashboardOutlined />,
      label: "Dashboard",
    },
    {
      key: "stocks-group",
      icon: <DatabaseOutlined />,
      label: "Stocks",
      children: [
        { key: "/stocks/master", label: "Stock Master" },
        { key: "/stocks/dates", label: "Dates" },
        { key: "/stocks/statements", label: "Statements" },
        { key: "/stocks/metrics", label: "Metrics" },
        { key: "/stocks/facts", label: "Financial Facts" },
        { key: "/stocks/explorer", label: "Stock Explorer" },
      ],
    },
    {
      key: "/logout",
      icon: <LogoutOutlined />,
      label: "Logout",
    },
  ];

  const handleMenuClick = ({ key }) => {
    if (key === "/logout") {
      setToken(null);
      window.location.href = "/";
      return;
    }

    if (key.startsWith("/")) {
      navigate(key);
    }
  };

  return (
    <Sider collapsible collapsed={collapsed} trigger={null} style={{ minHeight: "100vh" }}>
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
        {!collapsed && <span>IDBMS</span>}
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
        selectedKeys={[location.pathname]}
        defaultOpenKeys={["stocks-group"]}
        items={items}
        onClick={handleMenuClick}
      />
    </Sider>
  );
}