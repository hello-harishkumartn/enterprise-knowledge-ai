FROM python:3.12-slim

WORKDIR /app

# Build deps for any packages that need to compile (kept minimal); removed
# after install to keep the image slim (sentence-transformers/torch already
# dominate the image size — this is a portfolio/demo image, not a
# size-optimized production one; see docs/DEPLOYMENT.md).
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1 \
    STORAGE_DIR=/app/storage

RUN mkdir -p /app/storage

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
