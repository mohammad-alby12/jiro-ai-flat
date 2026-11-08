#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/backend"
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
[ -f ../.env ] || cp ../.env.example ../.env
uvicorn app.main:app --host 127.0.0.1 --port 8000
