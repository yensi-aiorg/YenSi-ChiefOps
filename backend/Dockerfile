FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libcairo2-dev \
        libpango1.0-dev \
        libgdk-pixbuf2.0-dev \
        libffi-dev \
        shared-mime-info && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.11-slim AS runtime

LABEL maintainer="YenSi ChiefOps Team"
LABEL description="ChiefOps Backend API"

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libcairo2 \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libpangoft2-1.0-0 \
        libgdk-pixbuf2.0-0 \
        libffi8 \
        shared-mime-info \
        fonts-liberation \
        fonts-dejavu-core \
        curl && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -r chiefops && \
    useradd -r -g chiefops -d /app -s /sbin/nologin chiefops

COPY --from=builder /install /usr/local

WORKDIR /app

COPY app/ ./app/

RUN chown -R chiefops:chiefops /app

USER chiefops

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop", "--http", "httptools", "--access-log", "--log-level", "info"]
