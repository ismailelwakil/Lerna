# Academic OS — Railway production image (FastAPI + AI service)
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    HF_HOME=/app/.cache/huggingface \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence-transformers

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY ai-service/requirements.txt /app/ai-service/requirements.txt
COPY requirements.txt /app/requirements.txt

# CPU PyTorch first (avoids huge CUDA wheels), then remaining deps
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch \
    && pip install -r /app/requirements.txt

COPY . /app

# Writable data dirs (Railway volume can be mounted over /app/ai-service/data)
RUN mkdir -p /app/ai-service/data/profiles \
             /app/ai-service/data/uploads \
             /app/ai-service/data/artifacts \
             /app/ai-service/data/chroma \
    && chmod -R a+rwX /app/ai-service/data

# Pre-download embedding model so first request is not a 400MB download
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small')" \
    || echo "WARN: embedding model pre-download skipped (will fetch at runtime)"

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/" || exit 1

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

CMD ["sh", "/app/start.sh"]
