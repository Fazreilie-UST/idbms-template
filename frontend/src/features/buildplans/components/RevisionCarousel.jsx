import { useMemo, useRef } from "react";
import {
  Button,
  Card,
  Descriptions,
  Empty,
  Space,
  Tag,
  Tooltip,
  Typography,
} from "antd";
import {
  LeftOutlined,
  PlusOutlined,
  RightOutlined,
} from "@ant-design/icons";

const { Text, Title } = Typography;

const LOCKED_STATUSES = new Set(["cancelled"]);

// Static fallback list of warehouse-stash names. Mirrors
// backend/app/scripts/seed_build_plan.py::WAREHOUSE_MAPPING. Used so that a
// warehouse row that somehow leaks into the "samples" section of an Excel
// column (whitespace / case quirks) is still excluded from the build-request
// list when the per-revision warehouse_quantities snapshot is empty or uses
// a normalised name.
const WAREHOUSE_STASH_NAMES = new Set([
  "cnb5",
  "odm",
  "odm to keep for test",
]);

function renderListSummary(rows, formatter) {
  if (!rows || rows.length === 0) {
    return <Text type="secondary">—</Text>;
  }
  return (
    <Space orientation="vertical" size={2} style={{ width: "100%" }}>
      {rows.map((row, i) => (
        <Text key={i} style={{ fontSize: 12 }}>
          {formatter(row)}
        </Text>
      ))}
    </Space>
  );
}

function partitionBuildRequests(rows, warehouseNames) {
  // Some build-plan files mix three kinds of rows into the "samples"
  // section: real per-user build requests, a per-group total row (the
  // group's name as the "requester"), and warehouse stash rows. We separate
  // them here so the UI can render groups with their declared totals and
  // drop the warehouse rows entirely.
  const normalize = (s) =>
    String(s ?? "")
      .replace(/\u00a0/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  const wh = new Set([
    ...WAREHOUSE_STASH_NAMES,
    ...(warehouseNames || []).map(normalize),
  ]);
  const knownGroupNames = new Set();
  for (const r of rows || []) {
    if (r.recipient) {
      knownGroupNames.add(normalize(r.recipient));
    }
  }

  const groupTotalsByName = new Map(); // lower-cased name -> { label, quantity }
  const groupMembers = new Map(); // lower-cased group name -> items[]
  const ungrouped = [];

  for (const r of rows || []) {
    const name = String(r.requester ?? "").trim();
    const lower = normalize(name);
    if (!name) continue;
    if (wh.has(lower)) continue; // warehouse row — handled in warehouse section
    // Defensive: any requester string that contains a known warehouse-stash
    // token is treated as a warehouse stash row (catches "ODM ", "ODM keep",
    // etc. where the file may not match the canonical name exactly).
    if (
      Array.from(wh).some(
        (whName) => whName.length >= 3 && lower.includes(whName)
      )
    ) {
      continue;
    }

    if (knownGroupNames.has(lower)) {
      // This row is the group total (requester == group name).
      groupTotalsByName.set(lower, { label: name, quantity: r.quantity });
      continue;
    }

    if (r.recipient) {
      const key = normalize(r.recipient);
      if (!groupMembers.has(key)) groupMembers.set(key, []);
      groupMembers.get(key).push(r);
    } else {
      ungrouped.push(r);
    }
  }

  // Build the ordered list of groups. Use the union of names seen as
  // recipient values and as explicit total rows.
  const groupKeys = new Set([
    ...groupMembers.keys(),
    ...groupTotalsByName.keys(),
  ]);
  const groups = Array.from(groupKeys).map((key) => {
    const total = groupTotalsByName.get(key);
    const items = (groupMembers.get(key) || []).slice();
    items.sort((a, b) =>
      (a.requester || "").localeCompare(b.requester || "")
    );
    const sum = items.reduce(
      (acc, x) => acc + (Number(x.quantity) || 0),
      0
    );
    return {
      label: total?.label || items[0]?.recipient || key,
      declaredTotal:
        total?.quantity !== undefined && total?.quantity !== null
          ? Number(total.quantity)
          : null,
      computedTotal: sum,
      items,
    };
  });
  groups.sort((a, b) => (a.label || "").localeCompare(b.label || ""));
  ungrouped.sort((a, b) =>
    (a.requester || "").localeCompare(b.requester || "")
  );

  // Member count = everything we will actually render as a member line
  // (i.e. excludes group-total and warehouse-stash rows).
  const memberCount =
    groups.reduce((acc, g) => acc + g.items.length, 0) + ungrouped.length;

  return { groups, ungrouped, memberCount };
}

function renderBuildRequestsByGroup(rows, warehouseNames) {
  const { groups, ungrouped } = partitionBuildRequests(rows, warehouseNames);
  if (groups.length === 0 && ungrouped.length === 0) {
    return <Text type="secondary">—</Text>;
  }
  return (
    <Space orientation="vertical" size={8} style={{ width: "100%" }}>
      {groups.map((g, gi) => {
        const total =
          g.declaredTotal !== null ? g.declaredTotal : g.computedTotal;
        return (
          <div key={`g-${gi}`}>
            <div style={{ marginBottom: 2 }}>
              <Tag color="geekblue" style={{ fontSize: 11 }}>
                {g.label}: {total}
              </Tag>
              {g.declaredTotal !== null &&
                g.declaredTotal !== g.computedTotal && (
                  <Text type="warning" style={{ fontSize: 11, marginLeft: 6 }}>
                    (members sum: {g.computedTotal})
                  </Text>
                )}
            </div>
            {g.items.length === 0 ? (
              <Text
                type="secondary"
                style={{ fontSize: 12, paddingLeft: 8, display: "block" }}
              >
                — no members —
              </Text>
            ) : (
              g.items.map((row, i) => (
                <Text
                  key={`g-${gi}-${i}`}
                  style={{ fontSize: 12, paddingLeft: 8, display: "block" }}
                >
                  • {row.requester}: {row.quantity}
                </Text>
              ))
            )}
          </div>
        );
      })}
      {ungrouped.length > 0 && (
        <div>
          {groups.length > 0 && (
            <Tag style={{ fontSize: 11, marginBottom: 2 }}>Ungrouped</Tag>
          )}
          {ungrouped.map((row, i) => (
            <Text
              key={`u-${i}`}
              style={{ fontSize: 12, paddingLeft: 8, display: "block" }}
            >
              • {row.requester}: {row.quantity}
            </Text>
          ))}
        </div>
      )}
    </Space>
  );
}

// ---------------------------------------------------------------------------
// Client-side fallback diff
//
// `changed_fields` is computed at write time on the backend (see
// build_plan_revision_service.diff_snapshot) and stored in the
// build_plan_revisions table. Some revisions — legacy rows, rows produced by
// a re-attribution branch, or rows where the previous diff was lost — may
// arrive with an empty `changed_fields`. For those we recompute a diff in
// the browser from the persisted snapshots so the user still sees what
// changed.
// ---------------------------------------------------------------------------

function _rowKey(row, keyFields) {
  return keyFields.map((f) => String(row?.[f] ?? "")).join("\u0001");
}

function _rowsEqual(a, b) {
  // Snapshot rows are flat dicts of scalars; compare via stable JSON.
  const keys = new Set([...Object.keys(a || {}), ...Object.keys(b || {})]);
  for (const k of keys) {
    if (String(a?.[k] ?? "") !== String(b?.[k] ?? "")) return false;
  }
  return true;
}

function _diffRows(oldRows, newRows, keyFields) {
  const oldByKey = new Map((oldRows || []).map((r) => [_rowKey(r, keyFields), r]));
  const newByKey = new Map((newRows || []).map((r) => [_rowKey(r, keyFields), r]));
  const added = [];
  const removed = [];
  const changed = [];
  for (const [k, v] of newByKey) {
    if (!oldByKey.has(k)) added.push(v);
    else if (!_rowsEqual(oldByKey.get(k), v)) {
      changed.push({ before: oldByKey.get(k), after: v });
    }
  }
  for (const [k, v] of oldByKey) {
    if (!newByKey.has(k)) removed.push(v);
  }
  if (added.length === 0 && removed.length === 0 && changed.length === 0) {
    return null;
  }
  return { added, removed, changed };
}

function computeClientDiff(prevSnapshot, newSnapshot) {
  const out = {};
  const oldPlan = prevSnapshot?.plan || {};
  const newPlan = newSnapshot?.plan || {};
  const planDiff = {};
  const planKeys = new Set([...Object.keys(oldPlan), ...Object.keys(newPlan)]);
  for (const k of planKeys) {
    const a = oldPlan[k];
    const b = newPlan[k];
    // Deep-ish equality via JSON for arrays (e.g. build_notes).
    if (JSON.stringify(a ?? null) !== JSON.stringify(b ?? null)) {
      planDiff[k] = [a, b];
    }
  }
  if (Object.keys(planDiff).length > 0) out.plan = planDiff;

  const sectionKeys = {
    components: ["field"],
    tests: ["field"],
    build_requests: ["requester", "recipient"],
    warehouse_quantities: ["warehouse"],
  };
  for (const [section, keys] of Object.entries(sectionKeys)) {
    const d = _diffRows(
      prevSnapshot?.[section],
      newSnapshot?.[section],
      keys
    );
    if (d) out[section] = d;
  }
  return out;
}

function hasMeaningfulDiff(changedFields) {
  if (!changedFields || typeof changedFields !== "object") return false;
  if (changedFields.plan && Object.keys(changedFields.plan).length > 0) {
    return true;
  }
  for (const section of [
    "components",
    "tests",
    "build_requests",
    "warehouse_quantities",
  ]) {
    const c = changedFields[section];
    if (
      c &&
      ((c.added && c.added.length) ||
        (c.removed && c.removed.length) ||
        (c.changed && c.changed.length))
    ) {
      return true;
    }
  }
  return false;
}

function renderChangedFields(changedFields, isInitial = false, fallbackSource = null) {
  let safe =
    changedFields && typeof changedFields === "object" ? changedFields : {};

  // If the stored diff is empty (legacy row, re-attributed row, or a row
  // where only marker flags like __created__/__initial__ are set), but we
  // have both snapshots, recompute a diff client-side.
  if (!hasMeaningfulDiff(safe) && !isInitial && fallbackSource) {
    const { prevSnapshot, newSnapshot } = fallbackSource;
    if (prevSnapshot && newSnapshot) {
      safe = computeClientDiff(prevSnapshot, newSnapshot);
    }
  }

  // Note: the "initial revision" tag is rendered positionally on the
  // leftmost (smallest revision_number) card by RevisionCard, not via the
  // changed_fields markers. The `__created__` / `__initial__` flags are
  // retained as backend metadata but intentionally not surfaced as chips.

  const sections = [];

  // Plan-scalar field changes -------------------------------------------
  if (safe.plan && typeof safe.plan === "object") {
    const planRows = Object.entries(safe.plan);
    if (planRows.length > 0) {
      sections.push(
        <div key="plan">
          <Text strong style={{ fontSize: 11, color: "#000" }}>Plan</Text>
          <div>
            {planRows.map(([field, pair]) => (
              <Text
                key={field}
                style={{
                  fontSize: 11,
                  display: "block",
                  paddingLeft: 8,
                  color: "#000",
                }}
              >
                •{" "}
                <code
                  style={{
                    fontSize: 11,
                    color: "#000",
                    background: "rgba(150,150,150,0.1)",
                    border: "1px solid rgba(100,100,100,0.2)",
                    borderRadius: 3,
                    padding: "1px 4px",
                    margin: "0 2px",
                  }}
                >
                  {field}
                </code>
                :{" "}
                <Text
                  delete
                  style={{ fontSize: 11, color: "rgba(0,0,0,0.45)" }}
                >
                  {String(pair?.[0] ?? "∅")}
                </Text>{" "}
                →{" "}
                <Text style={{ fontSize: 11, color: "#000" }}>
                  {String(pair?.[1] ?? "∅")}
                </Text>
              </Text>
            ))}
          </div>
        </div>
      );
    }
  }

  // Row-level diffs for child sections ----------------------------------
  const ROW_FORMATTERS = {
    components: (r) => `${r.field}: ${r.value}`,
    tests: (r) => `${r.field}: ${r.value}`,
    build_requests: (r) =>
      `${r.requester}${r.recipient ? ` [${r.recipient}]` : ""}: ${r.quantity}`,
    warehouse_quantities: (r) => `${r.warehouse}: ${r.quantity}`,
  };

  for (const section of [
    "components",
    "tests",
    "build_requests",
    "warehouse_quantities",
  ]) {
    const change = safe[section];
    if (!change || typeof change !== "object") continue;
    const added = change.added || [];
    const removed = change.removed || [];
    const updated = change.changed || [];
    if (added.length === 0 && removed.length === 0 && updated.length === 0) {
      continue;
    }
    const fmt = ROW_FORMATTERS[section] || ((r) => JSON.stringify(r));
    sections.push(
      <div key={section}>
        <Text strong style={{ fontSize: 11, color: "#000" }}>
          {section.replace(/_/g, " ")}
        </Text>
        <div>
          {added.map((row, i) => (
            <Text
              key={`a-${i}`}
              style={{
                fontSize: 11,
                display: "block",
                paddingLeft: 8,
                color: "#389e0d",
              }}
            >
              + {fmt(row)}
            </Text>
          ))}
          {removed.map((row, i) => (
            <Text
              key={`r-${i}`}
              style={{
                fontSize: 11,
                display: "block",
                paddingLeft: 8,
                color: "#cf1322",
              }}
            >
              − {fmt(row)}
            </Text>
          ))}
          {updated.map((row, i) => (
            <Text
              key={`c-${i}`}
              style={{
                fontSize: 11,
                display: "block",
                paddingLeft: 8,
                color: "#1677ff",
              }}
            >
              ~ {fmt(row.before)} → {fmt(row.after)}
            </Text>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        marginTop: 8,
        paddingTop: 8,
        borderTop: "1px dashed #e0e0e0",
      }}
    >
      <Text
        strong
        style={{ fontSize: 12, display: "block", marginBottom: 4, color: "#000" }}
      >
        Changes from previous revision
      </Text>
      {sections.length === 0 ? (
        <Text type="secondary" style={{ fontSize: 11 }}>
          {isInitial
            ? "First recorded state — no prior revision to compare."
            : fallbackSource && fallbackSource.prevSnapshot
              ? "Snapshots are identical to the previous revision."
              : "No tracked changes for this revision."}
        </Text>
      ) : (
        <Space orientation="vertical" size={4} style={{ width: "100%" }}>
          {sections}
        </Space>
      )}
    </div>
  );
}

export default function RevisionCarousel({
  revisions = [],
  currentStatus,
  onAddRevisionClick,
  loading = false,
}) {
  const scrollerRef = useRef(null);
  const sorted = useMemo(() => {
    return [...revisions].sort((a, b) => {
      const ar = a.revision_number ?? 0;
      const br = b.revision_number ?? 0;
      return ar - br;
    });
  }, [revisions]);

  const statusLower = (currentStatus || "").toLowerCase();
  const addAllowed = !LOCKED_STATUSES.has(statusLower);

  const scrollBy = (delta) => {
    if (scrollerRef.current) {
      scrollerRef.current.scrollBy({ left: delta, behavior: "smooth" });
    }
  };

  return (
    <Card
      style={{ marginBottom: 24 }}
      title={
        <Space>
          <span>Revision History</span>
          <Tag>{sorted.length} revision{sorted.length === 1 ? "" : "s"}</Tag>
        </Space>
      }
      extra={
        <Space>
          <Button
            size="small"
            icon={<LeftOutlined />}
            onClick={() => scrollBy(-360)}
          />
          <Button
            size="small"
            icon={<RightOutlined />}
            onClick={() => scrollBy(360)}
          />
        </Space>
      }
      loading={loading}
    >
      {sorted.length === 0 ? (
        <Empty description="No revisions yet" />
      ) : (
        <div
          ref={scrollerRef}
          style={{
            display: "flex",
            gap: 16,
            overflowX: "auto",
            paddingBottom: 8,
            scrollSnapType: "x mandatory",
          }}
        >
          {sorted.map((rev, idx) => (
            <RevisionCard
              key={rev.revision_id}
              rev={rev}
              isInitial={idx === 0}
              prevRev={idx > 0 ? sorted[idx - 1] : null}
            />
          ))}
          <AddRevisionCard
            allowed={addAllowed}
            currentStatus={currentStatus}
            onClick={onAddRevisionClick}
          />
        </div>
      )}
    </Card>
  );
}

function RevisionCard({ rev, isInitial = false, prevRev = null }) {
  const snap = rev.snapshot || {};
  const plan = snap.plan || {};
  const components = snap.components || [];
  const tests = snap.tests || [];
  const orderRequests = snap.build_requests || [];
  const warehouses = snap.warehouse_quantities || [];
  const warehouseNames = warehouses.map((w) => w.warehouse).filter(Boolean);
  const orderRequestsPartition = partitionBuildRequests(
    orderRequests,
    warehouseNames
  );

  const fileLabel = rev.import_file_name
    ? rev.import_file_name
    : rev.import_file_id
      ? `file #${rev.import_file_id}`
      : "manual edit";

  return (
    <Card
      size="small"
      style={{
        minWidth: 360,
        maxWidth: 360,
        scrollSnapAlign: "start",
        flex: "0 0 auto",
      }}
      title={
        <Space>
          <span>Rev {rev.revision_number}</span>
          <Tag color="blue">{rev.status || plan.status || "—"}</Tag>
          {isInitial && (
            <Tag color="green">initial revision</Tag>
          )}          {rev.is_imported && (
            <Tag color="geekblue">Imported</Tag>
          )}        </Space>
      }
      extra={
        <Tooltip
          title={
            rev.work_year || rev.work_week
              ? `WW${String(rev.work_week ?? "??").padStart(2, "0")}/${rev.work_year ?? "??"}${rev.file_revision ? ` rev${rev.file_revision}` : ""}`
              : "No file metadata"
          }
        >
          <Text type="secondary" style={{ fontSize: 11 }}>
            {rev.work_year && rev.work_week
              ? `WW${String(rev.work_week).padStart(2, "0")}/${rev.work_year}`
              : "manual"}
          </Text>
        </Tooltip>
      }
    >
      <Descriptions
        size="small"
        column={1}
        styles={{
          label: { width: 130, fontSize: 12 },
          content: { fontSize: 12 },
        }}
      >
        <Descriptions.Item label="Support">
          {plan.support_activity || "—"}
        </Descriptions.Item>
        <Descriptions.Item label="Build Desc">
          {plan.build_description || "—"}
        </Descriptions.Item>
        <Descriptions.Item label="Product Code">
          {plan.product_code || "—"}
        </Descriptions.Item>
        <Descriptions.Item label="MM / TA">
          {(plan.mm_number || "—") + " / " + (plan.ta_number || "—")}
        </Descriptions.Item>
        <Descriptions.Item label="PBA / AS">
          {(plan.pba_number || "—") + " / " + (plan.as_number || "—")}
        </Descriptions.Item>
        <Descriptions.Item label="Required Qty">
          {plan.required_quantity ?? "—"}
        </Descriptions.Item>
        <Descriptions.Item label="Build Start Qty">
          {plan.build_start_quantity ?? "—"}
        </Descriptions.Item>
        <Descriptions.Item label="Est. Yield">
          {plan.estimated_yield != null ? `${plan.estimated_yield}%` : "—"}
        </Descriptions.Item>
        <Descriptions.Item label="Special Instr.">
          {plan.special_instruction || "—"}
        </Descriptions.Item>
        <Descriptions.Item label="Build Notes">
          {(plan.build_notes || []).length === 0 ? (
            "—"
          ) : (
            <Space wrap size={[2, 2]}>
              {plan.build_notes.map((n) => (
                <Tag key={n} style={{ fontSize: 11, padding: "0 4px" }}>
                  {n}
                </Tag>
              ))}
            </Space>
          )}
        </Descriptions.Item>
        <Descriptions.Item label={`Components (${components.length})`}>
          {renderListSummary(
            components,
            (r) => `${r.field}: ${r.value}`
          )}
        </Descriptions.Item>
        <Descriptions.Item label={`Tests (${tests.length})`}>
          {renderListSummary(tests, (r) => `${r.field}: ${r.value}`)}
        </Descriptions.Item>
        <Descriptions.Item
          label={`Order Reqs (${orderRequestsPartition.memberCount})`}
        >
          {renderBuildRequestsByGroup(orderRequests, warehouseNames)}
        </Descriptions.Item>
        <Descriptions.Item label={`Warehouses (${warehouses.length})`}>
          {renderListSummary(
            warehouses,
            (r) => `${r.warehouse}: ${r.quantity}`
          )}
        </Descriptions.Item>
      </Descriptions>

      {renderChangedFields(rev.changed_fields, isInitial, {
        prevSnapshot: prevRev?.snapshot,
        newSnapshot: rev.snapshot,
      })}

      <div style={{ marginTop: 8 }}>
        <Text type="secondary" style={{ fontSize: 11 }}>
          source: {fileLabel}
        </Text>
      </div>
    </Card>
  );
}

function AddRevisionCard({ allowed, currentStatus, onClick }) {
  const reason = !allowed
    ? `Current status '${currentStatus || "?"}' is locked. Manual revisions are not allowed on cancelled build plans.`
    : "Author a new revision with scalar field changes.";
  return (
    <Card
      size="small"
      style={{
        minWidth: 240,
        maxWidth: 240,
        scrollSnapAlign: "start",
        flex: "0 0 auto",
        background: allowed ? "#fafafa" : "#f5f5f5",
        border: allowed ? "1px dashed #1677ff" : "1px dashed #d9d9d9",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
      }}
      styles={{
        body: {
          textAlign: "center",
          padding: 16,
          width: "100%",
        },
      }}
    >
      <Title level={5} style={{ marginTop: 0 }}>
        + Add Revision
      </Title>
      <Tooltip title={reason}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          disabled={!allowed}
          onClick={onClick}
          style={{ marginTop: 8 }}
        >
          New Revision
        </Button>
      </Tooltip>
      <Text
        type="secondary"
        style={{ fontSize: 11, display: "block", marginTop: 12 }}
      >
        {allowed
          ? "Edits status & scalar fields. For component/test/order changes, re-import the build plan file."
          : reason}
      </Text>
    </Card>
  );
}
