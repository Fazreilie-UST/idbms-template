-- SELECT * FROM public.build_plan_components
-- ORDER BY id ASC 

SELECT
    cn.value AS build_plan,
	c.name AS component,
	cs.slot_code AS slot,
	s.name AS supplier_name
FROM build_plan_components bpc
LEFT JOIN build_plans bp ON bp.id = bpc.build_plan_id
LEFT JOIN config_numbers cn ON cn.id = bp.config_number_id
LEFT JOIN components c ON c.id = bpc.component_id
LEFT JOIN component_slots cs ON cs.id = bpc.slot_id
LEFT JOIN suppliers s ON s.id = bpc.supplier_id