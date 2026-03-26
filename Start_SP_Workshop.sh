#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec bash "$PROJECT_DIR/scripts/run_sp_workshop.sh"
