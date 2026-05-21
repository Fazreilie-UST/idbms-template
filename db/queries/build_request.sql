SELECT
    cn.value AS config_number,
    u.full_name,
    orq.quantity,
    orq.revision AS build_request_revision

FROM public.build_plan_build_requests bpor

JOIN public.build_plans bp
    ON bp.id = bpor.build_plan_id

LEFT JOIN public.config_numbers cn
    ON cn.id = bp.config_number_id

JOIN public.build_requests orq
    ON orq.id = bpor.build_request_id

JOIN public.users u
    ON u.id = orq.requestor_id

ORDER BY
    cn.value,
    u.full_name;