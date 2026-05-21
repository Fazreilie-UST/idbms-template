SELECT
    u.id            AS user_id,
    u.employee_id,
    u.email,
    u.full_name,
    u.is_active,
    COALESCE(STRING_AGG(r.role_name, ', ' ORDER BY r.role_name), '') AS roles
FROM users u
LEFT JOIN user_roles ur ON ur.user_id = u.id
LEFT JOIN roles      r  ON r.id       = ur.role_id
GROUP BY u.id, u.employee_id, u.email, u.full_name, u.is_active
ORDER BY u.id;