# syntax=docker/dockerfile:1.7

# ---------- Builder stage ----------
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---------- Runtime stage ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Non-root user
RUN groupadd --system --gid 1001 app \
    && useradd  --system --uid 1001 --gid app --no-create-home --shell /sbin/nologin app

WORKDIR /app

# Copy installed packages from the builder.
COPY --from=builder /install /usr/local

# Copy application code with correct ownership
COPY --chown=app:app . .

# Drop privileges
USER app

EXPOSE 8000

# Single uvicorn worker per container; scale via replicas.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
