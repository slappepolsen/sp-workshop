#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

if ! bash "$PROJECT_DIR/scripts/run_sp_workshop.sh"; then
  echo
  echo "SP Workshop failed to start."
  read -r -p "Press Enter to close..."
  exit 1
fi
