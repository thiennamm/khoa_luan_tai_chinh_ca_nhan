#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
test "${RENDER:-}" = true || { echo 'Start này chỉ dành cho Render.' >&2; exit 1; }
export DJANGO_SETTINGS_MODULE=config.render
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1
# Thay shell bằng Python; preflight và web dùng cùng process/cache model.
exec python -u -X utf8 scripts/render_start.py
