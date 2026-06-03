import React, { useRef, useCallback } from "react";
import { Card, Typography } from "antd";
import AuditLogTable from "./AuditLogTable";

const { Title, Paragraph } = Typography;

export default function AuditLogsPage({ triggerRefresh }: { triggerRefresh?: boolean }) {
  const auditTableRef = useRef<{ refresh: () => void }>(null);

  // Allow parent to trigger refresh
  const refreshAuditLogs = useCallback(() => {
    if (auditTableRef.current) auditTableRef.current.refresh();
  }, []);

  React.useEffect(() => {
    if (triggerRefresh) refreshAuditLogs();
  }, [triggerRefresh, refreshAuditLogs]);

  return (
    <Card style={{ maxWidth: 1100, margin: "0 auto", marginTop: 32, boxShadow: "0 2px 8px #f0f1f2" }}>
      <Title level={3} style={{ marginBottom: 0 }}>Audit Logs</Title>
      <Paragraph type="secondary" style={{ marginBottom: 24 }}>
        View all system audit logs. Only accessible by Admin and Developer roles.
      </Paragraph>
      <AuditLogTable ref={auditTableRef} />
    </Card>
  );
}
