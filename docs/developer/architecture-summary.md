# System Structure & Architecture

## Overview

The NPI DBMS is a three-tier web application:

```
┌────────────┐     HTTPS      ┌─────────────┐     SQL     ┌─────────────┐
│  Frontend  │ ─────────────► │   Backend   │ ──────────► │  PostgreSQL │
│ (React+TS) │                │  (FastAPI)  │             │             │
└────────────┘                └─────────────┘             └─────────────┘
                                     │
                                     ├──► Redis (rate-limit storage)
                                     └──► Local filesystem (uploads, docs)
```

## Repositories & key folders

- `frontend/` – Vite + React 19 + TypeScript + Ant Design + Zustand.
- `backend/` – FastAPI + SQLAlchemy + Alembic + Pydantic v2.
- `docs/` – User and developer documentation (this folder).
- `db/` – On-disk storage for uploaded data files (build plans, shipments,
  profile pictures).

## Security

- JWT access tokens delivered via httpOnly cookies, refreshed via
  `/api/v1/auth/refresh`.
- Double-submit CSRF (`X-CSRF-Token` header) on all mutating requests.
- Role-based access control via permission codes on every endpoint
  (`require_permission`, `require_any_permission`).
- Security headers, request-body size cap and rate limiting are applied
  globally as middleware.

## Deployment

The application is packaged with Docker Compose. See `docker-compose.yml`
at the repository root for service definitions.
