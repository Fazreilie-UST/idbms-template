SELECT
    cn.value AS config_number,
    t.name AS test,
    td.detail AS test_detail
FROM build_plan_tests bpt
JOIN build_plans bp
    ON bp.id = bpt.build_plan_id
LEFT JOIN config_numbers cn
    ON cn.id = bp.config_number_id
JOIN tests t
    ON t.id = bpt.test_id
LEFT JOIN test_details td
    ON td.id = bpt.test_detail_id
ORDER BY
    cn.value,
    t.name,
    td.detail;