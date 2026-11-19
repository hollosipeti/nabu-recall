#!/bin/sh
set -eu
export OPENAI_API_KEY="$(jq -r '.openai_api_key // ""' /data/options.json)"
export OPENAI_MODEL="$(jq -r '.openai_model // "gpt-4.1-mini"' /data/options.json)"
export BRIDGE_TOKEN="$(jq -r '.bridge_token // ""' /data/options.json)"
export DASHBOARD_PASSWORD="$(jq -r '.dashboard_password // ""' /data/options.json)"
export DB_PATH=/data/recall.sqlite3
cd /app
exec /venv/bin/python server.py
