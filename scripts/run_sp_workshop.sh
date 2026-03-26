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

if [[ ! -d ".venv" ]]; then
  echo "Creating virtual environment..."
  "$PYTHON_CMD" -m venv .venv
fi

VENV_PY="$PROJECT_DIR/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "Virtual environment is missing Python. Recreating .venv..."
  rm -rf .venv
  "$PYTHON_CMD" -m venv .venv
fi

MARKER="$PROJECT_DIR/.venv/.requirements_installed"
if [[ ! -f "$MARKER" || requirements.txt -nt "$MARKER" ]]; then
  echo "Installing requirements..."
  "$VENV_PY" -m pip install -r requirements.txt
  touch "$MARKER"
fi

echo "Starting SP Workshop..."
exec "$VENV_PY" app.py
