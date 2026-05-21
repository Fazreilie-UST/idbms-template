import { Form, Input, Button, Checkbox, Flex, message } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { login } from "@/features/auth/services/auth_service";
import { resetAuthGuard } from "@/shared/services/helper";
import { useAuthStore } from "@/shared/store/useAuthStore";

function decodeJwtPayload(token) {
  try {
    const payload = token.split(".")[1];
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(window.atob(normalized));
  } catch {
    return null;
  }
}

function getRoleFromLoginResponse(res) {
  const tokenPayload = res?.access_token ? decodeJwtPayload(res.access_token) : null;

  return (
    res?.user?.roles?.[0] ||
    tokenPayload?.roles?.[0] ||
    null
  );
}

function getDashboardPath(role) {
  if (role === "Program Manager" || role === "Admin") return "/pm/dashboard";
  if (role === "Requestor") return "/requestor/dashboard";
  return "/";
}

export default function Login() {
  const navigate = useNavigate();
  const setUser = useAuthStore((state) => state.setUser);

  const onFinish = async (values) => {
    try {
      // Backend expects email, so map username/email input to email.
      const res = await login(values.username, values.password);
      const role = getRoleFromLoginResponse(res);

      if (!res?.user) {
        message.error("Login failed. No user info returned.");
        return;
      }

      if (!role) {
        message.error("Login succeeded, but user role was not returned.");
        return;
      }

      // Tokens are stored as httpOnly cookies by the backend; we only persist
      // role + display info in localStorage for UI bootstrapping.
      localStorage.setItem("role", role);

      const userObj = { ...(res.user || {}), role };
      localStorage.setItem("user", JSON.stringify(userObj));

      if (typeof setUser === "function") {
        setUser(userObj);
      }

      // Re-arm the global 401 handler for the new session.
      resetAuthGuard();

      navigate(getDashboardPath(role), { replace: true });
    } catch (error) {
      message.error(error?.response?.data?.detail || "Invalid username or password.");
    }
  };

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "90vh",
        width: "100%",
      }}
    >
      <div
        style={{
          width: 300,
          padding: 24,
          border: "1px solid #f0f0f0",
          borderRadius: 4,
          boxShadow: "0 2px 8px rgba(0, 0, 0, 0.1)",
          backgroundColor: "#e1d7ba",
        }}
      >
        <h2 style={{ textAlign: "center", marginBottom: 24, color: "#1e2331" }}>Login</h2>

        <Form
          name="login"
          initialValues={{ remember: true }}
          style={{ maxWidth: 360, width: "100%" }}
          onFinish={onFinish}
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: "Please input your username/email!" }]}
          >
            <Input prefix={<UserOutlined />} placeholder="Username or Email" />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: "Please input your password!" }]}
          >
            <Input.Password prefix={<LockOutlined />} placeholder="Password" />
          </Form.Item>

          <Form.Item>
            <Flex justify="space-between" align="center">
              <Form.Item name="remember" valuePropName="checked" noStyle>
                <Checkbox>Remember me</Checkbox>
              </Form.Item>
              <a href="/">Forgot password</a>
            </Flex>
          </Form.Item>

          <Form.Item>
            <Button block type="primary" htmlType="submit">
              Log in
            </Button>
          </Form.Item>
        </Form>
      </div>
    </div>
  );
}
