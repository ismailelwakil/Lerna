FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY tests ./tests
COPY data ./data

RUN useradd --create-home content && chown -R content:content /app
USER content

ENV CONTENT_ENV=production

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s \
  CMD curl -sf http://localhost:8000/health || exit 1

# web + in-process workers (single container; scale with --workers or replicas)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]