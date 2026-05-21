DROP SCHEMA public CASCADE;
CREATE SCHEMA public;


SELECT * FROM public.refresh_tokens
ORDER BY id ASC 


SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;