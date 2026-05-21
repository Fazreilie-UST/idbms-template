-- ----------------------------------------------------------------
-- Per (Family Code, SKU Name) builds & boards.
--
-- builds = number of distinct build plans with that (family, sku)
--          (cancelled build plans excluded by default)
-- boards = SUM over those build plans of
--              latest-revision build_request quantity
--            + warehouse stored quantity
--
-- Mirrors what the "Family x SKU breakdown" donut grid renders on the
-- Business Overview dashboard. Use this to sanity-check the API numbers.
-- ----------------------------------------------------------------

WITH latest_or AS (
    -- Total latest-revision build request quantity per build plan.
    -- Latest revision = no other OR has previous_build_request_id == this.id.
    -- Draft / Cancelled / Rejected ORs are excluded.
    SELECT
        bpor.build_plan_id,
        COALESCE(SUM(o.quantity), 0) AS or_qty
    FROM build_plan_build_requests bpor
    JOIN build_requests o ON o.id = bpor.build_request_id
    WHERE o.status NOT IN ('draft', 'cancelled', 'rejected')
      AND NOT EXISTS (
          SELECT 1 FROM build_requests o2
          WHERE o2.previous_build_request_id = o.id
      )
    GROUP BY bpor.build_plan_id
),

wh AS (
    -- Total warehouse-stored quantity per build plan.
    SELECT
        buildplan_id AS build_plan_id,
        COALESCE(SUM(quantity_stored), 0) AS wh_qty
    FROM quantity_stored_in_warehouse
    GROUP BY buildplan_id
),

bp_family_sku AS (
    -- One row per build plan tagged with its (family_code, sku_name)
    -- and pre-computed boards = or_qty + wh_qty.
    SELECT
        bp.id                                                AS build_plan_id,
        f.code                                               AS family_code,
        s.name                                               AS sku_name,
        s.code                                               AS sku_code,
        bp.year                                              AS year,
        bp.status                                            AS status,
        COALESCE(lor.or_qty, 0) + COALESCE(wh.wh_qty, 0)     AS boards
    FROM build_plans       bp
    JOIN family_skus       fs  ON fs.id = bp.family_sku_id
    JOIN families          f   ON f.id  = fs.family_id
    JOIN skus              s   ON s.id  = fs.sku_id
    LEFT JOIN latest_or    lor ON lor.build_plan_id = bp.id
    LEFT JOIN wh                ON wh.build_plan_id  = bp.id
    WHERE bp.status <> 'cancelled'        -- match dashboard default
    -- Optional filters (uncomment / parametrize as needed):
    -- AND bp.year = 2026
    -- AND f.code = 'WhP'
    -- AND s.name = 'Some SKU Name'
)

SELECT
    family_code,
    sku_name,
    COUNT(*)                  AS builds,
    COALESCE(SUM(boards), 0)  AS boards
FROM bp_family_sku
GROUP BY family_code, sku_name
ORDER BY family_code, boards DESC;
