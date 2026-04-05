#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

pick_python() {
  if command -v python3.12 >/dev/null 2>&1; then
    echo "python3.12"
  elif command -v python3 >/dev/null 2>&1; then
    echo "python3"
  elif command -v python >/dev/null 2>&1; then
    echo "python"
  else
    echo ""
  fi
}

PYTHON_CMD="$(pick_python)"
if [[ -z "$PYTHON_CMD" ]]; then
  echo "Python not found. Install Python 3.12 from https://www.python.org/downloads/"
  exit 1
fi

BASE_DIR="$HOME/VideoProcessingApp"
SHARED_VENV="$BASE_DIR/.venv"
PROJECT_VENV="$PROJECT_DIR/.venv"

mkdir -p "$BASE_DIR"

if [[ -d "$SHARED_VENV" ]]; then
  VENV_DIR="$SHARED_VENV"
elif [[ -d "$PROJECT_VENV" ]]; then
  VENV_DIR="$PROJECT_VENV"
else
  VENV_DIR="$SHARED_VENV"
  echo "Creating virtual environment..."
  "$PYTHON_CMD" -m venv "$VENV_DIR"
fi

VENV_PY="$VENV_DIR/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "Virtual environment is missing Python. Recreating venv..."
  rm -rf "$VENV_DIR"
  "$PYTHON_CMD" -m venv "$VENV_DIR"
  VENV_PY="$VENV_DIR/bin/python"
fi

REQ_HASH_FILE="$VENV_DIR/.requirements_hash"
REQ_MAIN="$PROJECT_DIR/requirements.txt"
REQ_WHISPER="$PROJECT_DIR/requirements-whisper-ai.txt"

export SP_PROJECT_DIR="$PROJECT_DIR"
NEW_HASH=$("$VENV_PY" - <<'PY'
import hashlib
import os
from pathlib import Path

p = Path(os.environ["SP_PROJECT_DIR"])
main = (p / "requirements.txt").read_bytes()
wh = (p / "requirements-whisper-ai.txt").read_bytes()
print(hashlib.sha256(main + wh).hexdigest())
PY
)

OLD_HASH=""
if [[ -f "$REQ_HASH_FILE" ]]; then
  OLD_HASH="$(tr -d '\n' <"$REQ_HASH_FILE")"
fi
if [[ "$NEW_HASH" != "$OLD_HASH" ]]; then
  echo "Installing requirements..."
  "$VENV_PY" -m pip install --upgrade pip
  # Whisper-ai first: only torch (large); then main so torchvision/torchaudio/openai-whisper resolve against it
  "$VENV_PY" -m pip install -r "$REQ_WHISPER" -r "$REQ_MAIN"
  printf '%s' "$NEW_HASH" > "$REQ_HASH_FILE"
fi

echo "Setup almost complete."
echo ""
echo "If the app doesn't start:"
echo "It will tell you what's missing (FFmpeg, etc.)"
echo ""
echo "Starting SP Workshop..."
export PATH="$VENV_DIR/bin:$PATH"
exec "$VENV_PY" "$PROJECT_DIR/app.py"
