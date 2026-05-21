import { useEffect, useState } from "react";
import { Card, Col, Row, Statistic, Skeleton } from "antd";
import {
  AppstoreOutlined,
  BookOutlined,
  ExperimentOutlined,
  StarOutlined,
  TagsOutlined,
} from "@ant-design/icons";
import { fetchKpis } from "../services/dashboard_service";
import { useDashboardFilters } from "../state/DashboardFiltersContext";
import ChartInfoTooltip from "./ChartInfoTooltip";

export default function KpiStrip() {
  const { filters } = useDashboardFilters();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchKpis(filters)
      .then((d) => !cancelled && setData(d))
      .catch(() => !cancelled && setData(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [filters]);

  const cards = [
    {
      title: "Total Builds",
      value: data?.total_builds ?? 0,
      icon: <BookOutlined />,
      info: "Total number of build plans within the current filter scope.",
    },
    {
      title: "Total Boards",
      value: Math.round(data?.total_boards ?? 0),
      icon: <AppstoreOutlined />,
      info: "Sum of board quantities required across all builds in scope.",
    },
    {
      title: "Families",
      value: data?.total_families ?? 0,
      icon: <TagsOutlined />,
      info: "Total number of Families registered in the catalog.",
    },
    {
      title: "Form Factors",
      value: data?.total_form_factors ?? 0,
      icon: <ExperimentOutlined />,
      info: "Total number of Form Factors registered in the catalog.",
    },
    {
      title: "Milestone Builds",
      value: data?.milestone_builds ?? 0,
      icon: <StarOutlined />,
      info: "Builds flagged as milestones within the current scope.",
    },
  ];

  return (
    <Row gutter={[12, 12]}>
      {cards.map((c) => (
        <Col xs={12} sm={8} md={Math.floor(24 / cards.length)} key={c.title}>
          <Card size="small">
            {loading ? (
              <Skeleton active paragraph={false} title={{ width: "80%" }} />
            ) : (
              <Statistic
                title={
                  <>
                    {c.title}
                    <ChartInfoTooltip title={c.info} />
                  </>
                }
                value={c.value}
                prefix={c.icon}
              />
            )}
          </Card>
        </Col>
      ))}
    </Row>
  );
}
