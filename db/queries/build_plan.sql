SELECT

    f.code AS family_code,
    ff.name AS form_factor,

    sa.name AS support_activity,
    bp.status,

    bpd.description AS build_description,

    COALESCE(
	    ARRAY_AGG(
	        DISTINCT bn.notes
	        ORDER BY bn.notes
	    ) FILTER (WHERE bn.notes IS NOT NULL),
	    '{}'
	) AS build_notes,

    cn.value AS config_number,

    latest_rev.revision_number AS revision,

    bp.product_code,
    bp.mm_number,
    bp.ta_number,
    bp.pba_number,
    bp.as_number,

    bp.special_instruction,
    bp.build_start_date,
    bp.ship_date,

    bp.required_quantity,
    bp.estimated_yield,
    bp.build_start_quantity,

    bp.year,
    bp.work_week

FROM build_plans bp

LEFT JOIN family_form_factors fff
    ON fff.id = bp.family_form_factor_id

LEFT JOIN families f
    ON f.id = fff.family_id

LEFT JOIN form_factors ff
    ON ff.id = fff.form_factor_id

LEFT JOIN support_activities sa
    ON sa.id = bp.support_activity_id

LEFT JOIN build_plan_build_descs bpd
    ON bpd.id = bp.build_description_id

LEFT JOIN build_plan_build_notes bpbn
    ON bpbn.build_plan_id = bp.id

LEFT JOIN build_notes bn
    ON bn.id = bpbn.build_note_id

LEFT JOIN config_numbers cn
    ON cn.id = bp.config_number_id

LEFT JOIN build_plan_revisions latest_rev
    ON latest_rev.id = bp.latest_revision_id

GROUP BY

    bp.id,
    f.code,
    ff.name,
    sa.name,
    bp.status,
    bpd.description,
    cn.value,
    latest_rev.revision_number

ORDER BY bp.id DESC

LIMIT 20 OFFSET 0;