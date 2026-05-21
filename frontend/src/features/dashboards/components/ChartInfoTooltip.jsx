import { Tooltip } from "antd";
import { ExclamationCircleOutlined } from "@ant-design/icons";

/**
 * Small hover-info indicator used in chart/card titles to clarify scope,
 * data caveats, and what the chart is counting. Renders an exclamation
 * circle that reveals descriptive text on hover.
 *
 * Usage:
 *   <Card title={<>My Chart <ChartInfoTooltip title="..." /></>} />
 *
 * Default copy notes that cancelled build plans are excluded, since this
 * is the most common gotcha across the Business Overview dashboard.
 */
export default function ChartInfoTooltip({
  title,
  placement = "top",
  iconStyle,
  excludesCancelled = true,
}) {
  const content = (
    <div style={{ maxWidth: 280, fontSize: 12, lineHeight: 1.5 }}>
      {title}
      {excludesCancelled && (
        <div style={{ marginTop: 6, opacity: 0.85 }}>
          Note: cancelled build plans are excluded from this chart.
        </div>
      )}
    </div>
  );

  return (
    <Tooltip title={content} placement={placement}>
      <ExclamationCircleOutlined
        style={{
          color: "currentColor",
          marginLeft: 6,
          cursor: "help",
          fontSize: 14,
          ...iconStyle,
        }}
      />
    </Tooltip>
  );
}
