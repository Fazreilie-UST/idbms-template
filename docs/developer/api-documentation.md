# API Documentation

The backend exposes an OpenAPI / Swagger schema at:

- **Swagger UI** – [`/docs`](http://localhost:8000/docs)
- **ReDoc** – [`/redoc`](http://localhost:8000/redoc)
- **OpenAPI JSON** – [`/openapi.json`](http://localhost:8000/openapi.json)

> The Documentation page embeds the live Swagger UI below this article so
> you can browse and try requests without leaving the application.

## Authentication

All `/api/v1/*` endpoints require a valid access token. The frontend signs
in via `/api/v1/auth/login`, which sets an httpOnly cookie that is sent
automatically on subsequent requests together with a double-submit CSRF
token (`X-CSRF-Token` header).

## Versioning

The API is mounted under `/api/v1`. Breaking changes will be introduced
behind a new version prefix; additive changes (new endpoints, optional
fields) are released in-place.
