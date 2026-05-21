-- ============================================================================
-- Remove build plans whose config_number does NOT start with the family code.
--
-- Relationship chain:
--   build_plans.family_form_factor_id -> family_form_factors.id
--   family_form_factors.family_id     -> families.id            (families.code)
--   build_plans.config_number_id      -> config_numbers.id      (config_numbers.value)
--
-- Expected format of config_numbers.value: "<FamilyCode><YY><WW>"
-- e.g. family.code = "ABC" -> config "ABC2632".
-- A value like "WW32" (no family code prefix) is considered invalid.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- 1) PREVIEW: list the offending build plans before deleting anything.
--    Run this first and sanity-check the rows.
-- ----------------------------------------------------------------------------
SELECT
    bp.id              AS build_plan_id,
    f.code             AS family_code,
    cn.value           AS config_number,
    LEFT(cn.value, 3)  AS config_first_3,
    bp.status,
    bp.ship_date
FROM build_plans bp
JOIN family_form_factors ff ON ff.id = bp.family_form_factor_id
JOIN families            f  ON f.id  = ff.family_id
JOIN config_numbers      cn ON cn.id = bp.config_number_id
WHERE
    -- Compare the prefix of config value against the actual family code.
    -- Use LEFT(cn.value, char_length(f.code)) so it works for family codes
    -- of any length (not just 3 chars).
    cn.value IS NULL
    OR f.code IS NULL
    OR LEFT(cn.value, char_length(f.code)) <> f.code
ORDER BY f.code, cn.value;


-- ----------------------------------------------------------------------------
-- 1b) Strict variant: enforce that the FIRST 3 CHARACTERS of the config
--     number equal the family code (as literally requested). Family codes
--     shorter/longer than 3 will be flagged here too.
-- ----------------------------------------------------------------------------
-- SELECT
--     bp.id, f.code, cn.value
-- FROM build_plans bp
-- JOIN family_form_factors ff ON ff.id = bp.family_form_factor_id
-- JOIN families            f  ON f.id  = ff.family_id
-- JOIN config_numbers      cn ON cn.id = bp.config_number_id
-- WHERE LEFT(cn.value, 3) <> f.code;


-- ----------------------------------------------------------------------------
-- 2) DELETE the offending build plans.
--    Wrap in a transaction so you can ROLLBACK if the row count looks wrong.
--
--    Most child tables (build_plan_revisions, build_plan_components,
--    build_plan_tests, build_plan_shippings, build_plan_build_notes,
--    build_plan_build_requests, build_plan_silicon_steppings,
--    build_plan_import_file_touches, build_plan_access_overrides) have
--    ON DELETE CASCADE at the DB level and are removed automatically.
--
--    EXCEPTION: quantity_stored_in_warehouse.buildplan_id has NO ON DELETE
--    CASCADE at the DB level (only an ORM-side cascade), so we must delete
--    those rows explicitly first. We also clear build_plans.latest_revision_id
--    to avoid the deferred self-FK during revision cascade.
-- ----------------------------------------------------------------------------
BEGIN;

CREATE TEMP TABLE bad_plans ON COMMIT DROP AS
SELECT bp.id
FROM build_plans bp
JOIN family_form_factors ff ON ff.id = bp.family_form_factor_id
JOIN families            f  ON f.id  = ff.family_id
JOIN config_numbers      cn ON cn.id = bp.config_number_id
WHERE cn.value IS NULL
   OR f.code  IS NULL
   OR LEFT(cn.value, char_length(f.code)) <> f.code;

-- Show what will be deleted.
SELECT COUNT(*) AS bad_plan_count FROM bad_plans;

-- 2a) Remove rows in tables whose FK to build_plans is NOT ON DELETE CASCADE.
DELETE FROM quantity_stored_in_warehouse
WHERE buildplan_id IN (SELECT id FROM bad_plans);

-- 2b) Break the build_plans -> build_plan_revisions self-reference before
--     the cascade removes the revisions.
UPDATE build_plans
SET latest_revision_id = NULL
WHERE id IN (SELECT id FROM bad_plans);

-- 2c) Finally delete the build plans (other children cascade automatically).
DELETE FROM build_plans
WHERE id IN (SELECT id FROM bad_plans);

-- Inspect the row count above, then either:
--   COMMIT;
-- or
--   ROLLBACK;
COMMIT;


-- ----------------------------------------------------------------------------
-- 3) OPTIONAL: clean up config_numbers that are now orphaned (no build_plan,
--    no build_request, no shipping references). Run only if you also want to
--    purge the bad config rows themselves.
-- ----------------------------------------------------------------------------
-- DELETE FROM config_numbers cn
-- WHERE NOT EXISTS (SELECT 1 FROM build_plans     bp WHERE bp.config_number_id = cn.id)
--   AND NOT EXISTS (SELECT 1 FROM build_requests  br WHERE br.config_number_id = cn.id)
--   AND NOT EXISTS (SELECT 1 FROM shippings       sh WHERE sh.config_number_id = cn.id);
