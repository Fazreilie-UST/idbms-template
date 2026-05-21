-- =====================================================================
-- Handler -> Recipients per build plan
--
-- For a given build plan config number, return one row per handler
-- (= the package recipient parsed from the build-plan Samples section's
--  SUM-formula cell), with the requestors / recipients aggregated into
-- a JSON list.
--
-- Output shape:
--     config_number | handler          | recipients
--     "ABCD-1"      | "Alice Example"  | [{"name":"Bob","quantity":5}, ...]
--
-- USAGE
--   pgAdmin / psql ad-hoc:   replace 'YOUR-CONFIG' below with the literal
--                            config number you want to query.
--   psql with variable:      \set cfg 'ABCD-1'   then swap the literal
--                            for :'cfg' in the WHERE clauses.
-- =====================================================================

SELECT
    cn.value                                AS config_number,
    handler.full_name                       AS handler,
    COALESCE(
        JSONB_AGG(
            JSONB_BUILD_OBJECT(
                'name',     requestor.full_name,
                'user_id',  requestor.id,
                'quantity', bps.quantity
            )
            ORDER BY requestor.full_name
        ) FILTER (WHERE requestor.id IS NOT NULL),
        '[]'::jsonb
    )                                       AS recipients,
    COUNT(*) FILTER (WHERE requestor.id IS NOT NULL) AS recipient_count,
    SUM(bps.quantity) FILTER (WHERE requestor.id IS NOT NULL) AS total_quantity
FROM build_plans bp
JOIN config_numbers cn          ON cn.id = bp.config_number_id
JOIN build_plan_shippings bps   ON bps.build_plan_id = bp.id
LEFT JOIN users handler         ON handler.id = bps.recipient_user_id
LEFT JOIN users requestor       ON requestor.id = bps.requestor_user_id
WHERE cn.value = 'YOUR-CONFIG'           -- <-- replace with your config_number
GROUP BY cn.value, handler.id, handler.full_name
ORDER BY handler.full_name NULLS LAST;


-- ---------------------------------------------------------------------
-- Variant: flat row-per-recipient (no aggregation) -- handy when you
-- want to feed the result into a table viewer that doesn't render JSON
-- nicely.
-- ---------------------------------------------------------------------
--
-- SELECT
--     cn.value                AS config_number,
--     handler.full_name       AS handler,
--     requestor.full_name     AS recipient,
--     bps.quantity            AS quantity
-- FROM build_plans bp
-- JOIN config_numbers cn          ON cn.id = bp.config_number_id
-- JOIN build_plan_shippings bps   ON bps.build_plan_id = bp.id
-- LEFT JOIN users handler         ON handler.id = bps.recipient_user_id
-- LEFT JOIN users requestor       ON requestor.id = bps.requestor_user_id
-- WHERE cn.value = 'YOUR-CONFIG'
-- ORDER BY handler.full_name NULLS LAST, requestor.full_name NULLS LAST;


-- ---------------------------------------------------------------------
-- Variant: comma-separated recipient names (single string column).
-- ---------------------------------------------------------------------
--
-- SELECT
--     cn.value                AS config_number,
--     handler.full_name       AS handler,
--     STRING_AGG(
--         requestor.full_name || ' (' || bps.quantity || ')',
--         ', '
--         ORDER BY requestor.full_name
--     ) FILTER (WHERE requestor.id IS NOT NULL) AS recipients
-- FROM build_plans bp
-- JOIN config_numbers cn          ON cn.id = bp.config_number_id
-- JOIN build_plan_shippings bps   ON bps.build_plan_id = bp.id
-- LEFT JOIN users handler         ON handler.id = bps.recipient_user_id
-- LEFT JOIN users requestor       ON requestor.id = bps.requestor_user_id
-- WHERE cn.value = 'YOUR-CONFIG'
-- GROUP BY cn.value, handler.id, handler.full_name
-- ORDER BY handler.full_name NULLS LAST;
