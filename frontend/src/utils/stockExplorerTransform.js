export function buildMetricTreeRows(rawRows) {
  const metricMap = new Map();
  const dateSet = new Set();

  for (const rawRow of rawRows) {
    const metricId =
      rawRow.metric_id ??
      rawRow["dim_metric.metric_id"] ??
      rawRow["metric.metric_id"];

    const metricName =
      rawRow.metric_name ??
      rawRow["dim_metric.metric_name"] ??
      rawRow["metric.metric_name"] ??
      "-";

    const parentMetricId =
      rawRow.parent_metric_id ??
      rawRow["dim_metric.parent_metric_id"] ??
      rawRow["metric.parent_metric_id"] ??
      null;

    const resolvedDate =
      rawRow.date ??
      rawRow["dim_date.date"] ??
      rawRow.period ??
      buildDateLabelFromYearMonth(rawRow);

    const value =
      rawRow.value ??
      rawRow["fact_financial_values.value"] ??
      rawRow["value"];

    if (metricId == null || !resolvedDate) {
      continue;
    }

    dateSet.add(resolvedDate);

    if (!metricMap.has(metricId)) {
      metricMap.set(metricId, {
        key: `metric-${metricId}`,
        metric_id: metricId,
        metric_name: metricName,
        parent_metric_id: parentMetricId,
        children: [],
      });
    }

    const metricNode = metricMap.get(metricId);
    metricNode.metric_name = metricName;
    metricNode.parent_metric_id = parentMetricId;
    metricNode[resolvedDate] = value;
  }

  const roots = [];

  for (const node of metricMap.values()) {
    const parentId = node.parent_metric_id;

    if (parentId != null && metricMap.has(parentId)) {
      metricMap.get(parentId).children.push(node);
    } else {
      roots.push(node);
    }
  }

  sortTreeRows(roots);

  const normalizedRows = cleanEmptyChildren(roots);
  const sortedDates = Array.from(dateSet).sort(comparePeriodLabel);

  return {
    rows: normalizedRows,
    dates: sortedDates,
  };
}

export function flattenTreeRowsForExport(treeRows, dateColumns, depth = 0) {
  const flat = [];

  for (const row of treeRows) {
    const hasChildren = !!row.children?.length;

    const item = {
      metric_name: row.metric_name || "-",
      depth,
      is_parent: hasChildren,
    };

    for (const dateKey of dateColumns) {
      item[dateKey] =
        row[dateKey] === null || row[dateKey] === undefined || row[dateKey] === ""
          ? ""
          : formatFinancialValue(row[dateKey]);
    }

    flat.push(item);

    if (hasChildren) {
      flat.push(...flattenTreeRowsForExport(row.children, dateColumns, depth + 1));
    }
  }

  return flat;
}

export function formatFinancialValue(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  const numericValue = Number(value);

  if (Number.isNaN(numericValue)) {
    return String(value);
  }

  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(numericValue);
}

function buildDateLabelFromYearMonth(row) {
  const year = row.year ?? row["dim_date.year"] ?? row["date.year"];
  const month = row.month ?? row["dim_date.month"] ?? row["date.month"];

  if (year == null) return null;
  if (month == null) return String(year);

  return `${year}-${String(month).padStart(2, "0")}`;
}

function sortTreeRows(nodes) {
  nodes.sort((a, b) => {
    const aName = a.metric_name || "";
    const bName = b.metric_name || "";
    return aName.localeCompare(bName);
  });

  nodes.forEach((node) => {
    if (node.children?.length) {
      sortTreeRows(node.children);
    }
  });
}

function cleanEmptyChildren(nodes) {
  return nodes.map((node) => {
    const cleanedChildren = node.children?.length
      ? cleanEmptyChildren(node.children)
      : [];

    if (cleanedChildren.length > 0) {
      return {
        ...node,
        children: cleanedChildren,
      };
    }

    const { children, ...rest } = node;
    return rest;
  });
}

function comparePeriodLabel(a, b) {
  const aDate = normalizePeriodForSort(a);
  const bDate = normalizePeriodForSort(b);

  if (aDate && bDate) {
    return aDate - bDate;
  }

  return String(a).localeCompare(String(b));
}

function normalizePeriodForSort(label) {
  if (!label) return null;

  if (/^\d{4}-\d{2}$/.test(label)) {
    return new Date(`${label}-01T00:00:00`);
  }

  if (/^\d{4}$/.test(label)) {
    return new Date(`${label}-01-01T00:00:00`);
  }

  const parsed = new Date(label);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}