import { Form, Input, Button, Checkbox, Flex } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { login } from "../services/auth_service";
import { useAuthStore } from "../store/useAuthStore";

export default function Login() {
  const setToken = useAuthStore((state) => state.setToken);

  const onFinish = async (values) => {
    // Note: backend still expects email, so map username → email
    const res = await login(values.username, values.password);
    setToken(res.access_token);
    window.location.href = "/dashboard";
  };

  return (
    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "90vh", width: "100%" }}>
      <div style={{ width: 300, padding: 24, border: "1px solid #f0f0f0", borderRadius: 4, boxShadow: "0 2px 8px rgba(0, 0, 0, 0.1)", backgroundColor: "#e1d7ba" }}>
        <h2 style={{ textAlign: "center", marginBottom: 24, color: "#1e2331" }}>Login</h2>
        <Form
          name="login"
          initialValues={{ remember: true }}
          style={{ maxWidth: 360, width: "100%" }}
          onFinish={onFinish}
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: "Please input your Username!" }]}
          >
            <Input prefix={<UserOutlined />} placeholder="Username" />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: "Please input your Password!" }]}
          >
            <Input
              prefix={<LockOutlined />}
              type="password"
              placeholder="Password"
            />
          </Form.Item>

          <Form.Item>
            <Flex justify="space-between" align="center">
              <Form.Item name="remember" valuePropName="checked" noStyle>
                <Checkbox>Remember me</Checkbox>
              </Form.Item>
              <a href="">Forgot password</a>
            </Flex>
          </Form.Item>

          <Form.Item>
            <Button block type="primary" htmlType="submit">
              Log in
            </Button>
            <div style={{ marginTop: "8px", textAlign: "center" }}>
              {/* or <a href="">Register now!</a> */}
            </div>
          </Form.Item>
        </Form>
      </div>
    </div>
  );
}