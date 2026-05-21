SELECT
    bp.id AS build_plan_id,
    cn.value AS config_number,
    w.id AS warehouse_id,
    w.name AS warehouse_name,
    COALESCE(q.quantity_stored, 0) AS quantity_stored
FROM public.build_plans bp
LEFT JOIN public.config_numbers cn
    ON cn.id = bp.config_number_id
CROSS JOIN public.warehouses w
LEFT JOIN public.quantity_stored_in_warehouse q
    ON q.buildplan_id = bp.id
   AND q.warehouse_id = w.id
ORDER BY bp.id, w.id;