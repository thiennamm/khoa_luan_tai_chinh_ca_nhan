"""Thuật toán chỉ nhận chuỗi tháng đã xác nhận; không ORM, không MoneyData."""
import math
from decimal import Decimal, ROUND_HALF_UP

from .forecast_config import CONFIG


class ForecastFailure(Exception):
    pass


def features(past):
    if len(past) < 12:
        raise ForecastFailure('Thiếu 12 tháng quá khứ để tạo đặc trưng.')
    return features_at(past, len(past))


def features_at(values, index):
    return [values[index-1], values[index-2], values[index-3], values[index-12],
            sum(values[index-3:index], Decimal('0')) / 3]


def clip(value):
    value = value if isinstance(value, Decimal) else Decimal(str(value))
    if not value.is_finite():
        raise ForecastFailure('Mô hình trả giá trị không hữu hạn.')
    return max(Decimal('0'), value)


def ridge_predict(past, alpha):
    # float64 chỉ ở ranh giới đại số ML; nguồn tổng tháng vẫn là Decimal VND.
    import numpy as np
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import Ridge

    x = np.asarray([features_at(past, index) for index in range(12, len(past))], dtype=np.float64)
    y = np.asarray(past[12:], dtype=np.float64)
    if len(y) == 0 or not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ForecastFailure('Dữ liệu huấn luyện ML không hợp lệ.')
    model = Pipeline([
        ('scaler', StandardScaler(**CONFIG['standard_scaler'])),
        ('ridge', Ridge(alpha=alpha, solver=CONFIG['ridge_solver'], fit_intercept=CONFIG['fit_intercept'])),
    ])
    # Không dùng launcher DLL, mô hình đã lưu hoặc dữ liệu từ thí nghiệm.
    model.fit(x, y)
    prediction = float(model.predict(np.asarray([features(past)], dtype=np.float64))[0])
    if not math.isfinite(prediction):
        raise ForecastFailure('Mô hình trả giá trị không hữu hạn.')
    return Decimal(str(prediction))


def method_predict(method, past):
    if method == 'mean3':
        return sum(past[-3:], Decimal('0')) / 3
    if method == 'previous':
        return past[-1]
    if method == 'seasonal':
        return past[-12]
    if method.startswith('ridge_'):
        return ridge_predict(past, float(method.split('_', 1)[1]))
    raise ForecastFailure('Phương pháp không hợp lệ.')


def choose_method(candidates):
    order = CONFIG['tie_order']
    return min(candidates, key=lambda item: (Decimal(item['mae']), order.index(item['method'])))['method']


def calculate(history):
    """history gồm month/date và forecast_expense/Decimal, chỉ quá khứ đã kết thúc."""
    values = [row['forecast_expense'] for row in history]
    if len(values) < CONFIG['minimum_months']:
        raise ForecastFailure('Cần ít nhất 3 tháng lịch sử hợp lệ liên tiếp.')
    if any(not isinstance(value, Decimal) or not value.is_finite() or value < 0 for value in values):
        raise ForecastFailure('Lịch sử còn tháng chưa biết hoặc giá trị không hợp lệ.')
    from .coverage_calendar import next_month
    for previous, current in zip(history, history[1:]):
        if next_month(previous['month']) != current['month']:
            raise ForecastFailure('Không nối lịch sử qua tháng thiếu.')
    candidates = []
    validation_months = []
    selected = 'mean3'
    try:
        if len(values) >= CONFIG['ml_minimum_months']:
            indexes = range(len(values) - CONFIG['validation_months'], len(values))
            validation_months = [history[index]['month'].isoformat() for index in indexes]
            for method in CONFIG['tie_order']:
                points = []
                errors = []
                for index in indexes:
                    predicted = clip(method_predict(method, values[:index]))
                    errors.append(abs(predicted - values[index]))
                    points.append({'month': history[index]['month'].isoformat(),
                                   'actual': str(values[index]), 'predicted': str(predicted)})
                candidates.append({'method': method, 'mae': str(sum(errors, Decimal('0')) / len(errors)),
                                   'points': points})
            selected = choose_method(candidates)
        predicted = clip(method_predict(selected, values))
        estimate = predicted.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        if len(str(abs(int(estimate)))) > 30:
            raise ForecastFailure('Ước tính vượt giới hạn hiển thị VND của chức năng.')
    except Exception as exc:
        # Không fallback baseline khi một bước ML thất bại; không lộ dữ liệu/lỗi DLL.
        if isinstance(exc, ForecastFailure):
            raise
        if len(values) < CONFIG['ml_minimum_months']:
            raise ForecastFailure('Không tính được ước tính theo trung bình 3 tháng. Chưa tạo kết quả mới.') from None
        raise ForecastFailure('Không chạy được bước ML thử nghiệm. Chưa tạo kết quả mới; không tự thay bằng baseline.') from None
    return {'method': selected, 'estimate': estimate, 'raw_estimate': str(predicted),
            'candidates': candidates, 'validation_months': validation_months,
            'regime': 'validation_selection' if candidates else 'mean3'}
