import { Layout } from "antd";
import { Outlet } from "react-router-dom";
import Sidebar from "@/shared/components/Sidebar";
import AppHeader from "@/shared/components/AppHeader";

const { Content } = Layout;

export default function MainLayout() {
  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sidebar />

      <Layout>
        <AppHeader />
        <Content
          style={{
            margin: "24px",
            padding: "24px",
            background: "#fff",
            borderRadius: "12px",
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
