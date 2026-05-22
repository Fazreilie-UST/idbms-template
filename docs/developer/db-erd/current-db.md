# Current Database ERD

The NPI DBMS uses a PostgreSQL database managed by SQLAlchemy + Alembic.

## High-level domains

- **auth** – users, roles, permissions, departments.
- **build** – build plans, revisions, components, attributes.
- **order** – build requests and their handlers.
- **stock** – stock allocations and financial events.
- **storage** – warehouses, addresses and shipping records.
- **audit** – append-only audit log of every CRUD against audited models.

## ERD

Replace this placeholder with an embedded image of the current database
ERD:

```
![Current DB ERD](/static/docs-assets/screenshots/current-db-erd.png)
```

Upload the image from the **Edit** panel (admin only) before referencing
it.
