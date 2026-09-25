#!/bin/sh
set -e
PORT="${PORT:-8000}"
exec uvicorn api.main:app \
  --host 0.0.0.0 \
  --port "$PORT" \
  --timeout-keep-alive 75 \
  --proxy-headers \
  --forwarded-allow-ips='*'
