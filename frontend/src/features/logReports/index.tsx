import React, { useCallback, useEffect, useState } from "react";
import { Card, Typography, Divider, message } from "antd";
import LogReportForm from "./LogReportForm";
import LogReportTable from "./LogReportTable";
import { useRef } from "react";
import axios from "axios";

const { Title, Paragraph } = Typography;

export default function LogReportsPage() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchReports = useCallback(() => {
    setLoading(true);
    axios.get("/api/v1/log-reports/my").then(res => {
      setReports(Array.isArray(res.data) ? res.data : []);
    }).catch(() => {
      message.error("Failed to fetch reports");
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const handleReportSubmitted = () => {
    fetchReports();
  };

  return (
    <Card style={{ maxWidth: 900, margin: "0 auto", marginTop: 32, boxShadow: "0 2px 8px #f0f1f2" }}>
      <Title level={3} style={{ marginBottom: 0 }}>Report an Issue or Bug</Title>
      <Paragraph type="secondary" style={{ marginBottom: 24 }}>
        Submit a bug or issue report about the system. Our team will review and address it promptly.
      </Paragraph>
      <LogReportForm onSubmitted={handleReportSubmitted} />
      <Divider orientation="left">Your Submitted Reports</Divider>
      <LogReportTable reports={reports} loading={loading} />
      {/* Recent Audit Logs table removed as requested */}
    </Card>
  );
}
