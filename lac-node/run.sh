#!/usr/bin/env bash
set -e
cd /root/LightAnonChain-/lac-node
exec .venv/bin/gunicorn lac_node:app \
  --workers 3 \
  --worker-class gthread \
  --threads 8 \
  --bind 0.0.0.0:38400 \
  --timeout 120 \
  --log-level warning \
  -- --datadir /root/LightAnonChain-/lac-node/data --port 38400
