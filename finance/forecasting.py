import hashlib
import json
import platform
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from django.db import transaction

from .coverage import monthly_history
from .coverage_calendar import current_month
from .coverage_state import lock_coverage_writes
from .forecast_config import CONFIG
from .forecast_math import ForecastFailure, calculate
from .models import ForecastDataVersion, ForecastResult, MonthlyCoverage


def shift_month(month, count):
    index = month.year * 12 + month.month - 1 + count
    return date(index // 12, index % 12 + 1, 1)


def configuration():
    runtime = {'python': platform.python_version()}
    for package in ['scikit-learn', 'numpy', 'scipy']:
        try:
            runtime[package] = version(package)
        except PackageNotFoundError:
            runtime[package] = 'missing'
    names = ['forecasting.py', 'forecast_math.py', 'forecast_config.py', 'coverage.py',
             'coverage_calendar.py', 'coverage_state.py', 'forecast_state.py', 'transaction_queries.py', 'signals.py', 'models.py']
    engine = hashlib.sha256()
    for name in names:
        engine.update(name.encode() + (Path(__file__).parent / name).read_bytes())
    return {'design': CONFIG, 'runtime': runtime, 'engine_sha256': engine.hexdigest()}


@transaction.atomic
def snapshot(user):
    target = current_month()
    last = shift_month(target, -1)
    revision = ForecastDataVersion.objects.filter(user=user).values_list('version', flat=True).first() or 0
    states = {row.month: row for row in MonthlyCoverage.objects.filter(user=user, month__lte=last)}
    cursor = last
    tail = []
    while cursor in states and states[cursor].status == MonthlyCoverage.Status.COMPLETE:
        tail.append(cursor)
        if cursor == date.min:
            break
        cursor = shift_month(cursor, -1)
    tail.reverse()
    first = tail[0] if tail else shift_month(target, -3)
    rows = monthly_history(user, first, last)
    eligible = rows if tail else []
    required = []
    if len(eligible) < CONFIG['minimum_months']:
        for step in [-3, -2, -1]:
            month = shift_month(target, step)
            status = states[month].status if month in states else MonthlyCoverage.Status.UNKNOWN
            if status != MonthlyCoverage.Status.COMPLETE:
                required.append({'month': month, 'status_display': MonthlyCoverage.Status(status).label})
    config = configuration()
    payload = {'user': user.pk, 'target': target.isoformat(), 'revision': revision, 'configuration': config,
               'history': [{'month': row['month'].isoformat(), 'expense': str(row['forecast_expense']),
                            'status': row['status'], 'confirmed_at': row['confirmed_at'].isoformat() if row['confirmed_at'] else None,
                            'transaction_count': row['transaction_count']} for row in rows],
               'required': [{'month': row['month'].isoformat(), 'status': row['status_display']} for row in required]}
    fingerprint = hashlib.sha256(json.dumps(payload, ensure_ascii=True, sort_keys=True).encode()).hexdigest()
    return {'target': target, 'history': eligible, 'history_count': len(eligible), 'required': required,
            'fingerprint': fingerprint, 'configuration': config}


class StaleForecast(ForecastFailure):
    pass


def compute_and_store(user, source):
    # Việc fit nằm ngoài transaction đọc/ghi để không khóa SQLite lâu.
    result = calculate(source['history'])
    with transaction.atomic():
        lock_coverage_writes([user.pk], 'default')
        fresh = snapshot(user)
        if fresh['fingerprint'] != source['fingerprint']:
            raise StaleForecast('Dữ liệu, xác nhận, cấu hình hoặc tháng đích đã thay đổi khi tính. Hãy kiểm tra và tính lại.')
        history = source['history']
        return ForecastResult.objects.update_or_create(user=user, defaults={
            'target_month': source['target'], 'fingerprint': source['fingerprint'],
            'history_count': len(history), 'history_start': history[0]['month'], 'history_end': history[-1]['month'],
            'method': result['method'], 'estimate': str(result['estimate']),
            'configuration': source['configuration'],
            'details': {key: value for key, value in result.items() if key not in ['method', 'estimate']},
        })[0]
