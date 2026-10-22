#!/usr/bin/env bash
set -euo pipefail
# Không set -x: command tracing có thể lộ biến bí mật.
cd "$(dirname "$0")/.."
test "${RENDER:-}" = true || { echo 'Build này chỉ dành cho Render.' >&2; exit 1; }
export DJANGO_SETTINGS_MODULE=config.render
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 BLIS_NUM_THREADS=1
python -X utf8 -m pip install --disable-pip-version-check --progress-bar off -r requirements-render.txt
python -X utf8 -m pip check
python -X utf8 scripts/download_inference_bundle.py
python -X utf8 manage.py collectstatic --noinput --settings=config.render
python -X utf8 manage.py check --deploy --settings=config.render
python -X utf8 manage.py check_inference_models --settings=config.render
# Migrations chỉ chạy khi start; không cần pre-deploy command trả phí.
