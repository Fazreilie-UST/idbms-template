import { Layout } from "antd";
import { Outlet } from "react-router-dom";
import Sidebar from "../components/action/Sidebar";

const { Content } = Layout;

export default function MainLayout() {
  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sidebar />

      <Layout>
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