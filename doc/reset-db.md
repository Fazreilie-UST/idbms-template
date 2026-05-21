remove alembic migration

DROP SCHEMA public CASCADE;
CREATE SCHEMA public;

source .venv/bin/activate
alembic revision --autogenerate -m "initial schema"
python -m alembic upgrade head
python -m app.scripts.seed_rbac
python -m app.scripts.seed_initial_db
python -m app.scripts.seed_build_plan
python -m app.scripts.seed_shipments
python -m uvicorn app.main:app --reload

(PGADMIN LOGIN)
Email : npi_admin@intel.com
Password : NPI-test



python -m app.scripts.cleanup_refresh_tokens ----> automate later to run it weekly
    cron job
    Celery beat
    APScheduler
    Kubernetes CronJob
    GitHub Actions scheduled job