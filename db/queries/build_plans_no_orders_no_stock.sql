-- Build plans whose status is NOT 'cancelled' AND
--   * have no build requests linked, AND
--   * have no quantity stored at any warehouse (no row, or all rows = 0).
-- Uses the latest revision per config_number (bp.latest_revision_id).

SELECT
    cn.value                       AS config_number,
    f.code                         AS family_code,
    s.code                         AS sku_code,
    bp.id                          AS build_plan_id,
    bp.product_code,
    bp.status,
    bp.required_quantity,
    latest_rev.revision_number     AS latest_revision,
    latest_rev.work_year,
    latest_rev.work_week,
    latest_rev.file_revision
FROM public.build_plans bp
JOIN public.config_numbers cn
    ON cn.id = bp.config_number_id
JOIN public.build_plan_revisions latest_rev
    ON latest_rev.id = bp.latest_revision_id
LEFT JOIN public.family_skus fs
    ON fs.id = bp.family_sku_id
LEFT JOIN public.families f
    ON f.id = fs.family_id
LEFT JOIN public.skus s
    ON s.id = fs.sku_id
WHERE
    bp.status IS DISTINCT FROM 'cancelled'

    -- No build requests linked to this build plan
    AND NOT EXISTS (
        SELECT 1
        FROM public.build_plan_build_requests bpor
        WHERE bpor.build_plan_id = bp.id
    )

    -- No quantity stored at any warehouse (no row, or all rows are zero)
    AND NOT EXISTS (
        SELECT 1
        FROM public.quantity_stored_in_warehouse q
        WHERE q.buildplan_id = bp.id
          AND COALESCE(q.quantity_stored, 0) > 0
    )
ORDER BY cn.value;
