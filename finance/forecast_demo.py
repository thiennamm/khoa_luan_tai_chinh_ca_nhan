"""Kịch bản tổng hợp cố định; không đọc/ghi dữ liệu tài khoản hoặc MoneyData."""
import copy
import hashlib
import json
import random
from datetime import date
from decimal import Decimal
from pathlib import Path
from threading import Lock

from .forecast_math import calculate
from .forecasting import configuration, shift_month


DEMO = {
    'version': 'synthetic-vnd-demo-v1',
    'seed': 9048,
    'first_month': '2022-01-01',
    'months': 48,
    'target': '2026-01-01',
    'base_vnd': 6000000,
    'trend_vnd_per_month': 35000,
    'seasonal_vnd': [900000, 400000, -200000, -100000, 0, 200000,
                     300000, 100000, -150000, 0, 250000, 700000],
    'noise_integer_vnd': [-600000, 600000],
}
_lock = Lock()
_cached = None  # Một kịch bản công khai, chỉ trong RAM; không user ID/session/ORM.


def scenario():
    rng = random.Random(DEMO['seed'])
    first = date.fromisoformat(DEMO['first_month'])
    history = []
    for index in range(DEMO['months']):
        amount = (DEMO['base_vnd'] + DEMO['trend_vnd_per_month'] * index
                  + DEMO['seasonal_vnd'][index % 12]
                  + rng.randint(*DEMO['noise_integer_vnd']))
        history.append({'month': shift_month(first, index),
                        'forecast_expense': Decimal(max(0, amount))})
    target = date.fromisoformat(DEMO['target'])
    if shift_month(history[-1]['month'], 1) != target:
        raise ValueError('Tháng đích demo phải liền sau lịch sử.')
    data = [{'month': row['month'].isoformat(), 'expense': str(row['forecast_expense'])}
            for row in history]
    digest = lambda value: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    data_hash = digest(data)
    config = configuration()
    config = {**config, 'design': {**config['design'],
              'target': 'fixed illustrative month; synthetic monthly expense in VND'}}
    fingerprint = digest({'demo': DEMO, 'data_sha256': data_hash, 'engine': config,
                          'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()})
    return {'history': history, 'target': target, 'data_sha256': data_hash,
            'fingerprint': fingerprint, 'configuration': config,
            'demo': copy.deepcopy(DEMO)}


def cached_result(source):
    """GET chỉ đọc RAM. Mỗi tiến trình có cache riêng; restart thì bấm POST lại."""
    with _lock:
        if _cached and _cached['fingerprint'] == source['fingerprint']:
            return copy.deepcopy(_cached['result'])
    return None


def run_demo(source):
    global _cached
    # Dùng nguyên bộ chọn phương pháp 08D; không dùng compute_and_store(user,...).
    result = calculate(source['history'])
    with _lock:
        _cached = {'fingerprint': source['fingerprint'], 'result': copy.deepcopy(result)}
    return result


def chart(source, result):
    """Tọa độ SVG; float chỉ dùng vẽ, không dùng cộng tiền/lựa chọn phương pháp."""
    values = [row['forecast_expense'] for row in source['history']]
    scale_max = max(values + ([result['estimate']] if result else [])) * Decimal('1.15')
    scale_max = max(scale_max, Decimal(1))
    def point(index, value):
        return {'x': format(55 + index * 820 / 48, '.2f'),
                'y': format(245 - float(value / scale_max) * 210, '.2f')}
    points = [point(index, value) for index, value in enumerate(values)]
    output = {'history': ' '.join(f"{p['x']},{p['y']}" for p in points),
              'top_vnd': scale_max, 'last': points[-1]}
    if result:
        predicted = point(48, result['estimate'])
        output.update(predicted=predicted,
                      forecast=f"{points[-1]['x']},{points[-1]['y']} {predicted['x']},{predicted['y']}")
    return output
