#!/usr/bin/env bash
set -e
cd /home/fbinalex/NPI-IDBMS/backend
source .venv/bin/activate
python -c "from app.api.v1.endpoints import build_plans; from app.services import build_plan_revision_service; print('OK', len(build_plans.router.routes), 'routes')"
