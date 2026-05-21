#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
python3 -c "from app.main import app; print('OK')"
