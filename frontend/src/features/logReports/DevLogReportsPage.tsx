import React, { useCallback, useEffect, useState } from "react";
import { Card, Typography, message } from "antd";
import LogReportTable from "./LogReportTable";
import axios from "axios";

const { Title } = Typography;

export default function DevLogReportsPage() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchReports = useCallback(() => {
    setLoading(true);
    axios.get("/api/v1/log-reports").then(res => {
      setReports(Array.isArray(res.data) ? res.data : []);
    }).catch(() => {
      message.error("Failed to fetch reports");
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  return (
    <Card style={{ maxWidth: 1100, margin: "0 auto", marginTop: 32, boxShadow: "0 2px 8px #f0f1f2" }}>
      <Title level={3} style={{ marginBottom: 0 }}>Bug Reports</Title>
      <LogReportTable reports={reports} loading={loading} devMode onUpdated={fetchReports} />
    </Card>
  );
}
