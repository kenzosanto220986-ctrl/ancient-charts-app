#!/usr/bin/env bash
# Start "Αρχαίοι χάρτες" locally.  Usage: ./start.sh [port]     (default 8765, bound to 127.0.0.1 only)
set -euo pipefail
cd "$(dirname "$0")"
PORT="${1:-${PORT:-8765}}"
if [ ! -d .venv ]; then
  echo ">> Creating virtualenv and installing dependencies..."
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
# Optional LLM for the chat (see README):  export XAI_API_KEY=...   or   OPENAI_API_KEY=...   or   LLM_API_KEY + LLM_BASE_URL + LLM_MODEL
echo ">> http://127.0.0.1:${PORT}   (Ctrl+C to stop)"
# --no-access-log: do not write requested URLs (city searches) to logs
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --no-access-log
