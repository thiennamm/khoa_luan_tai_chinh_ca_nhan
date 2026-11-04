#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test "${RENDER:-}" = true || { echo 'Start bảo trì chỉ dành cho Render.' >&2; exit 1; }
# This file/module is absent on old releases: an old release cannot serve traffic.
# Never print the key or enable shell tracing.
python -X utf8 -c 'from scripts.maintenance_gate import require_maintenance_start; require_maintenance_start()'
exec bash deploy/render-start.sh
