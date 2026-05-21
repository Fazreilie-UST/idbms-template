-- Per-config-number revision history. One row per (config_number, revision)
-- showing the import file that produced it and a summary of what changed.
-- Only config_numbers with more than one revision are returned.

SELECT
    cn.value                       AS config_number,
    f.code                         AS family_code,
    ff.name                        AS form_factor,
    bp.id                          AS build_plan_id,
    bpr.revision_number,
    bpr.work_year,
    bpr.work_week,
    bpr.file_revision,
    bpr.status_at_revision         AS status,
    bpr.changed_fields,
    bpr.created_at,
    bpif.id                        AS import_file_id,
    bpif.original_filename         AS import_file_name
FROM build_plans bp
JOIN config_numbers cn
    ON cn.id = bp.config_number_id
JOIN build_plan_revisions bpr
    ON bpr.build_plan_id = bp.id
LEFT JOIN family_form_factors fff
    ON fff.id = bp.family_form_factor_id
LEFT JOIN families f
    ON f.id = fff.family_id
LEFT JOIN form_factors ff
    ON ff.id = fff.form_factor_id
LEFT JOIN build_plan_import_files bpif
    ON bpif.id = bpr.import_file_id
WHERE bp.id IN (
    SELECT build_plan_id
    FROM build_plan_revisions
    GROUP BY build_plan_id
    HAVING COUNT(*) > 1
)
ORDER BY cn.value, bpr.revision_number;


-- Touches: import files that referenced a build plan but produced no diff.
-- SELECT
--     cn.value                AS config_number,
--     bp.id                   AS build_plan_id,
--     bpif.id                 AS import_file_id,
--     bpif.original_filename  AS import_file_name,
--     bpif.work_year,
--     bpif.work_week,
--     bpif.file_revision,
--     t.matched_revision_id,
--     t.created_at
-- FROM build_plan_import_file_touches t
-- JOIN build_plans bp ON bp.id = t.build_plan_id
-- JOIN config_numbers cn ON cn.id = bp.config_number_id
-- JOIN build_plan_import_files bpif ON bpif.id = t.import_file_id
-- ORDER BY cn.value, bpif.created_at;

