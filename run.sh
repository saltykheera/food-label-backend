#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "====================================================="
echo "  🥗 Food Label Analyzer API - Backend Server        "
echo "====================================================="

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

echo "Starting Backend API on http://0.0.0.0:8000..."
echo "Swagger Documentation: http://localhost:8000/docs"
echo "Press Ctrl+C to stop."
echo "====================================================="

exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
