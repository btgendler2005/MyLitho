#!/bin/bash
set -e
cd "$(dirname "$0")"

PORT=8420
URL="http://127.0.0.1:$PORT"

if [ ! -d ".venv" ]; then
  echo "First-time setup — this only happens once, may take a minute..."
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install --upgrade pip -q
  pip install -r requirements.txt -q
  echo "Setup complete."
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

if curl -s -o /dev/null "$URL"; then
  echo "MyLitho is already running — opening your browser."
  open "$URL"
  exit 0
fi

echo "Starting MyLitho..."
uvicorn app.main:app --host 127.0.0.1 --port "$PORT" &
SERVER_PID=$!
trap 'kill $SERVER_PID 2>/dev/null' EXIT

for _ in $(seq 1 40); do
  if curl -s -o /dev/null "$URL"; then
    break
  fi
  sleep 0.25
done

open "$URL"
echo ""
echo "MyLitho is running at $URL"
echo "Leave this window open while you use it — close it (or press Ctrl+C) to stop the server."

wait $SERVER_PID
