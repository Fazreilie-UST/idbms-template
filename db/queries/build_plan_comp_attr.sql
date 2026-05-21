SELECT
    cn.value AS config_number,
    c.name AS component,
    cs.slot_code AS slot,
    ad.name AS attribute,
    COALESCE(
        cav.value_text,
        cav.value_number::text
    ) AS value
FROM build_plans bp
LEFT JOIN config_numbers cn
    ON cn.id = bp.config_number_id
JOIN build_plan_components bpc
    ON bpc.build_plan_id = bp.id
JOIN components c
    ON c.id = bpc.component_id
LEFT JOIN component_slots cs
    ON cs.id = bpc.slot_id
JOIN component_attribute_values cav
    ON cav.build_plan_component_id = bpc.id
JOIN attribute_definitions ad
    ON ad.id = cav.attribute_id
ORDER BY
    cn.value,
    c.name,
    cs.slot_code,
    ad.name;