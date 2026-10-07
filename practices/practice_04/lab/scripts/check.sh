#!/usr/bin/env bash
# Optional bash wrapper — canonical runner is: python scripts/check.py
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python "$SCRIPT_DIR/check.py" "$@"
