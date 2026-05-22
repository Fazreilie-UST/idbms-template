import { Card, Typography } from "antd";
import { resolveBackendUrl } from "@/config";

/**
 * Embed the backend's auto-generated Swagger UI inside the documentation
 * page. The iframe loads `/docs` on the API origin so it is always in sync
 * with the live OpenAPI schema.
 */
export default function SwaggerEmbed() {
  const swaggerUrl = resolveBackendUrl("/docs") ?? "/docs";
  return (
    <Card
      size="small"
      title="Swagger UI"
      style={{ marginTop: 24 }}
      extra={
        <Typography.Link
          href={swaggerUrl}
          target="_blank"
          rel="noopener noreferrer"
        >
          Open in new tab ↗
        </Typography.Link>
      }
      styles={{ body: { padding: 0 } }}
    >
      <iframe
        title="Swagger UI"
        src={swaggerUrl}
        style={{
          width: "100%",
          height: "80vh",
          border: 0,
        }}
      />
    </Card>
  );
}
