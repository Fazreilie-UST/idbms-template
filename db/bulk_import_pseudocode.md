# Build Plan Bulk Import — Revision-Aware Design

## Goals

- **One row per `(family_sku, config_number)`** in `build_plans` (the "canonical"
  / "latest state" row). The Build Plan Tracker page reads this directly.
- Every imported file that introduces a real change produces **one
  `BuildPlanRevision`** row → append-only history per config number.
- Files that contain the config but introduce **no changes** do NOT create a
  revision and do NOT pollute `audit_logs`. They are recorded in
  `BuildPlanImportFileTouch` so we can answer *"was this file processed against
  this config?"* without inflating history.
- The canonical row always reflects the **latest revision's** status + data.
  Children (components, tests, build requests, warehouse quantities) mirror the
  latest revision too.
- A file is considered "later" than an existing revision by chronological key
  `(work_year, work_week, file_revision)`. Files may arrive out of order, so
  we may need to insert revisions mid-history.

---

## Data model changes

### `BuildPlan` (modified)

- **Drop** the unique constraint
  `(family_sku_id, config_number_id, work_year, work_week, file_revision)`.
- **Add** unique constraint `(family_sku_id, config_number_id)`.
- **Add** columns:
  - `latest_revision_id` → FK to `build_plan_revisions(id)` (nullable until
    first revision exists; in practice always set after import).
  - `first_seen_file_id`, `last_seen_file_id` → FK to
    `build_plan_import_files(id)`, both ON DELETE SET NULL.
- **Keep** scalar columns (status, dates, quantities, special_instruction,
  build_description_id, support_activity_id, mm/ta/pba/as numbers, …). They
  always hold the *latest* value.
- **Remove** `work_week`, `work_year`, `file_revision`, `revision`,
  `import_file_id` from `BuildPlan` — that data now lives on
  `BuildPlanRevision`.

### `BuildPlanRevision` (new, append-only)

```
id                   PK
build_plan_id        FK -> build_plans (ON DELETE CASCADE)
revision_number      int     -- 1,2,3 …  in chronological order
import_file_id       FK -> build_plan_import_files (ON DELETE SET NULL)
work_year            int
work_week            int
file_revision        int
snapshot             JSON    -- full snapshot of plan + children at this revision
changed_fields       JSON    -- row-level diff vs previous revision (see below)
status_at_revision   Enum(BuildPlanStatus)   -- denormalised for fast tracker queries
created_at           datetime

UNIQUE (build_plan_id, revision_number)
INDEX  (build_plan_id, work_year, work_week, file_revision)
```

### `BuildPlanImportFileTouch` (new)

```
id                     PK
import_file_id         FK -> build_plan_import_files (ON DELETE CASCADE)
build_plan_id          FK -> build_plans (ON DELETE CASCADE)
matched_revision_id    FK -> build_plan_revisions (ON DELETE SET NULL)
created_at             datetime

UNIQUE (import_file_id, build_plan_id)
```

A row is written every time a file is processed against an existing
`BuildPlan` and the parser determined that this file is a re-issue of an
already-known revision (no diff).

### `audit_logs`

Emit **one entry per `BuildPlanRevision`** created (module=`BuildPlan`,
action=`CREATE` for first revision, `UPDATE` otherwise, `new_value` =
`changed_fields`). No audit entries for `BuildPlanImportFileTouch`.

---

## Snapshot + diff conventions

A **snapshot** is a JSON dict shaped like:

```jsonc
{
  "plan": {
    "status": "Plan",
    "support_activity": "...",
    "build_description": "...",
    "product_code": "...",
    "mm_number": "...",
    "ta_number": "...",
    "pba_number": "...",
    "as_number": "...",
    "special_instruction": "...",
    "build_start_date": "2026-04-13",
    "ship_date": "2026-04-27",
    "required_quantity": 100,
    "estimated_yield": 95,
    "build_start_quantity": 110,
    "build_notes": ["note A", "note B"]            // sorted
  },
  "components": [                                  // sorted by (component_code, attributes)
    {"code": "...", "quantity": 4, "attributes": {...}}
  ],
  "tests": [                                       // sorted by test name
    {"name": "...", "quantity": 5, "detail": {...}}
  ],
  "build_requests": [                              // sorted by requester full_name
    {
      "requester": "Alex Tan",
      "recipient": "...",
      "quantity": 3
    }
  ],
  "warehouse_quantities": [                        // sorted by warehouse code
    {"warehouse": "PG10", "quantity": 12}
  ]
}
```

`diff_snapshot(old, new)` returns `{}` iff the two snapshots are equal,
otherwise an object describing changes:

```jsonc
{
  "plan": {
    "status":            ["Plan", "Hold"],         // only ever present here
    "ship_date":         ["2026-04-27", "2026-05-04"],
    "required_quantity": [100, 120]
  },
  "components": {
    "added":   [ {...full row...} ],
    "removed": [ {...full row...} ],
    "changed": [ {"key": "...", "before": {...}, "after": {...}} ]   // full row-level diff
  },
  "tests":               { "added": [...], "removed": [...], "changed": [...] },
  "build_requests":      { "added": [...], "removed": [...], "changed": [...] },
  "warehouse_quantities":{ "added": [...], "removed": [...], "changed": [...] }
}
```

Per your spec:
- **Plan-level**: every field-level diff is recorded (status, dates,
  quantities, notes, numbers).
- **Children**: full row-level diffs (`added` / `removed` / `changed`).
  `changed` carries the whole `before` and `after` row, not per-field deltas.
- **Build requests**: equality = same requester + same recipient + same
  quantity. Any other field change is ignored for diff purposes.

---

## Status monotonicity rule

You said the case where a newer file regresses status should not happen —
when it does, **throw an error**, mark the file `failed`, and leave the
build plan untouched. Allowed transition order:

```
New  <  Plan  <  Hold  <  Done
              <         <  Cancelled
```

(Hold ↔ Plan are both fine; Done / Cancelled are terminal.)

- **CASE A (latest-wins)** — if the incoming status would regress vs the
  canonical row, raise `ImportError(f"Config {cfg}: status would regress
  from {old} -> {new}")`. The whole file's transaction is rolled back so
  partially-applied changes don't leak.
- **CASE B / C (insert mid-history or as initial)** — canonical row not
  affected, no status check.

---

## Per-file processing pseudocode

```
process_import_file(file):
    require file.work_year, file.work_week, file.file_revision   # else mark file 'skipped'
    chrono_in = (file.work_year, file.work_week, file.file_revision)

    for each parsed_column in file:
        cfg = clean(parsed_column.build_info["Config Number"])
        if cfg is empty or cfg.upper() == "TBD": skip column, count as skipped

        family_sku = get_family_sku(parsed_column.family, parsed_column.sku)
        incoming_snapshot = build_snapshot(parsed_column)

        bp = BuildPlan.find(family_sku, cfg)

        # ---------- NEW build plan ----------
        if bp is None:
            bp = BuildPlan.create(scalar fields from parsed_column)
            attach_children(bp, parsed_column)        # components, tests, orders, wh
            rev = BuildPlanRevision.create(
                build_plan         = bp,
                revision_number    = 1,
                import_file        = file,
                work_year/week/rev = chrono_in,
                snapshot           = incoming_snapshot,
                changed_fields     = {"__created__": true},
                status_at_revision = bp.status,
            )
            bp.latest_revision_id = rev.id
            bp.first_seen_file_id = file.id
            bp.last_seen_file_id  = file.id
            emit_audit(action=CREATE, record_id=bp.id, new_value=incoming_snapshot)
            continue

        # ---------- EXISTING build plan: find chrono position ----------
        revisions = bp.revisions ordered by (work_year, work_week, file_revision) ASC
        if any rev in revisions has chrono == chrono_in:
            # Same exact chrono key already exists. Treat as touch.
            record_touch(file, bp, matched_revision = that rev)
            continue

        prev_rev = last revision with chrono <  chrono_in   (or None)
        next_rev = first revision with chrono >  chrono_in  (or None)

        # ===== CASE A: incoming file is the NEWEST =====
        if next_rev is None:
            assert prev_rev is not None    # otherwise revisions list was empty,
                                           # which contradicts bp existing
            diff = diff_snapshot(prev_rev.snapshot, incoming_snapshot)

            if diff is empty:
                record_touch(file, bp, matched_revision = prev_rev)
                bp.last_seen_file_id = file.id
                continue

            # Status monotonicity check (latest-wins case only).
            if "status" in diff.plan:
                old_status, new_status = diff.plan["status"]
                if violates_monotonic_order(old_status, new_status):
                    raise ImportError(
                        f"Config {cfg}: status would regress from "
                        f"{old_status} -> {new_status}"
                    )

            rev = BuildPlanRevision.create(
                build_plan         = bp,
                revision_number    = prev_rev.revision_number + 1,
                import_file        = file,
                work_year/week/rev = chrono_in,
                snapshot           = incoming_snapshot,
                changed_fields     = diff,
                status_at_revision = incoming_snapshot.plan.status,
            )

            apply_scalars_to_bp(bp, parsed_column)        # status, dates, qtys, notes, …
            replace_children(bp, parsed_column)           # full reseed from parsed data
            bp.latest_revision_id = rev.id
            bp.last_seen_file_id  = file.id

            emit_audit(action=UPDATE, record_id=bp.id,
                       old_value=prev_rev.snapshot, new_value=incoming_snapshot)

        # ===== CASE B: incoming file slots BETWEEN two existing revisions =====
        elif prev_rev is not None and next_rev is not None:
            diff_prev = diff_snapshot(prev_rev.snapshot, incoming_snapshot)
            diff_next = diff_snapshot(incoming_snapshot, next_rev.snapshot)

            if diff_prev is empty:
                # File is a re-issue of prev_rev — no new revision needed.
                record_touch(file, bp, matched_revision = prev_rev)
                continue

            if diff_next is empty:
                # File is the *true* origin of what we recorded as next_rev.
                # Rewrite next_rev's source pointers/chrono to this file.
                next_rev.import_file_id = file.id
                next_rev.work_year      = file.work_year
                next_rev.work_week      = file.work_week
                next_rev.file_revision  = file.file_revision
                continue

            # Genuine in-between revision. Shift later revision_numbers up by 1.
            shift_revision_numbers(bp, start_at = next_rev.revision_number, by = +1)

            BuildPlanRevision.create(
                build_plan         = bp,
                revision_number    = next_rev.revision_number,   # now vacated
                import_file        = file,
                work_year/week/rev = chrono_in,
                snapshot           = incoming_snapshot,
                changed_fields     = diff_prev,
                status_at_revision = incoming_snapshot.plan.status,
            )
            # NOTE: canonical bp scalars + children are NOT touched in CASE B.
            # latest_revision_id stays pointed at the truly-latest revision.
            emit_audit(action=UPDATE, record_id=bp.id,
                       old_value=prev_rev.snapshot, new_value=incoming_snapshot,
                       extra={"inserted_mid_history": true})

        # ===== CASE C: incoming file is OLDER than every existing revision =====
        else:    # prev_rev is None, next_rev is not None
            diff_next = diff_snapshot(incoming_snapshot, next_rev.snapshot)

            if diff_next is empty:
                # Earliest known revision actually came from this file.
                next_rev.import_file_id = file.id
                next_rev.work_year      = file.work_year
                next_rev.work_week      = file.work_week
                next_rev.file_revision  = file.file_revision
                bp.first_seen_file_id   = file.id
                continue

            # Shift everyone up by 1, insert this as revision_number = 1.
            shift_revision_numbers(bp, start_at = 1, by = +1)

            BuildPlanRevision.create(
                build_plan         = bp,
                revision_number    = 1,
                import_file        = file,
                work_year/week/rev = chrono_in,
                snapshot           = incoming_snapshot,
                changed_fields     = {"__created__": true},
                status_at_revision = incoming_snapshot.plan.status,
            )
            bp.first_seen_file_id = file.id
            # bp.latest_* untouched.
            emit_audit(action=UPDATE, record_id=bp.id,
                       new_value=incoming_snapshot,
                       extra={"inserted_as_initial": true})
```

### Helpers

- `build_snapshot(parsed_column) -> dict` — converts parsed Excel column into
  the canonical JSON snapshot shape (sorted lists for determinism).
- `snapshot_of(bp) -> dict` — same shape but built from existing DB rows
  (used during the data backfill and as a safety net).
- `diff_snapshot(old, new) -> dict` — returns `{}` if equal, else the diff
  structure described above.
- `record_touch(file, bp, matched_revision)` — upsert into
  `BuildPlanImportFileTouch`. Also updates `bp.last_seen_file_id` if
  `file.chrono >= bp.latest_revision.chrono`.
- `shift_revision_numbers(bp, start_at, by)` — single UPDATE that bumps every
  revision_number ≥ `start_at` by `by`. Executed inside the same transaction
  as the insert so the unique constraint is honoured.
- `apply_scalars_to_bp(bp, parsed_column)` — copies plan-level scalars onto
  the canonical row.
- `replace_children(bp, parsed_column)` — `delete` + `add` for components,
  tests, build requests, warehouse quantities (the ORM `cascade="all,
  delete-orphan"` relationships already support this).
- `violates_monotonic_order(old, new)` — returns True iff
  `old ∈ {Done, Cancelled}` and `new ∈ {New, Plan, Hold}`,
  OR `old == Hold` and `new == New`.

### Per-file summary fields (replaces today's `build_plans_processed`)

```
revisions_created            int   -- CASE A new-revision + CASE B/C inserted
revisions_inserted_midstream int   -- CASE B/C only
no_change_touches            int   -- record_touch invocations
new_build_plans              int   -- "NEW build plan" branch
status_errors                list  -- monotonicity violations (file marked failed)
columns_skipped              int
unrecorded_users             list
warnings                     list
```

---

## Migration / backfill

1. New tables: `build_plan_revisions`, `build_plan_import_file_touches`.
2. Alter `build_plans`: drop old unique, add new unique
   `(family_sku_id, config_number_id)`, add `latest_revision_id`,
   `first_seen_file_id`, `last_seen_file_id`. Drop `work_week`, `work_year`,
   `file_revision`, `revision`, `import_file_id`.
3. Backfill (data migration):
   - Group existing `build_plans` by `(family_sku_id, config_number_id)`.
   - Order rows in each group by `(work_year, work_week, file_revision)` ASC.
   - Keep the **latest** row as the canonical `BuildPlan`.
   - For every row in the group create a `BuildPlanRevision`
     (`revision_number` = 1..N, `snapshot = snapshot_of(old_row)`,
     `changed_fields` computed by diffing against the previous snapshot).
   - Re-point each row's children onto the canonical `BuildPlan`. Where two
     historical rows had *different* child sets, the canonical row keeps the
     latest set; earlier sets live only in `BuildPlanRevision.snapshot`.
   - Set `latest_revision_id`, `first_seen_file_id`, `last_seen_file_id`.

---

## UI impact

- **Build Plan Tracker** lists `BuildPlan` rows → one per `(family_sku,
  config_number)`. Columns: status (from canonical row),
  `revision_number = bp.latest_revision.revision_number`, `last_seen_file`, …
- A **detail drawer / page** shows:
  - Revision timeline (oldest → newest) with `changed_fields` chips per entry
    and link to source `import_file`.
  - "Touched without change" list from `BuildPlanImportFileTouch`.
- **Build Plan Imports** page summary chips switch from
  `processed / duplicated` to `revisions_created /
  revisions_inserted_midstream / no_change_touches / status_errors`.
