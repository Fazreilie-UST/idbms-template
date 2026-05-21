#!/usr/bin/env bash
set -e
cd /home/fbinalex/NPI-IDBMS/backend
source .venv/bin/activate
rm -f alembic/versions/*_initial_schema.py
python - <<'PY'
from app.core.config import settings
from sqlalchemy import create_engine, text
url = getattr(settings, "SQLALCHEMY_DATABASE_URI", None) or getattr(settings, "DATABASE_URL", None) or settings.database_url
e = create_engine(url)
with e.connect() as c:
    c.execute(text("COMMIT"))
    c.execute(text("DROP SCHEMA public CASCADE"))
    c.execute(text("CREATE SCHEMA public"))
    c.execute(text("COMMIT"))
print("schema reset OK")
PY
alembic revision --autogenerate -m "initial schema" 2>&1 | tail -n 60
echo "----- upgrade head -----"
python -m alembic upgrade head 2>&1 | tail -n 40
