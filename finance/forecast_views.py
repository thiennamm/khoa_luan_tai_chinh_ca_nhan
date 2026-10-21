from decimal import Decimal
from datetime import date

from django.contrib.auth.decorators import login_required
from django.db import OperationalError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .forecast_config import CONFIG, METHOD_LABELS
from .forecast_math import ForecastFailure
from .forecasting import compute_and_store, snapshot
from .models import ForecastResult


@login_required
@require_http_methods(['GET', 'POST'])
@never_cache
def forecast(request):
    try:
        source = snapshot(request.user)
    except Exception:
        return render(request, 'finance/forecast.html', {'error': 'Chưa kiểm tra được lịch sử. Vui lòng thử lại; chưa hiển thị kết quả cũ.'}, status=503)
    context = {'source': source}
    saved = ForecastResult.objects.filter(user=request.user).first()
    valid = saved is not None and saved.target_month == source['target'] and saved.fingerprint == source['fingerprint']
    context['stale'] = saved is not None and not valid
    if request.method == 'POST' and source['history_count'] >= CONFIG['minimum_months']:
        try:
            compute_and_store(request.user, source)
        except ForecastFailure as exc:
            context['error'] = str(exc)
            # Không hiện kết quả cũ như thể vừa tính thành công hoặc fallback ML.
            return render(request, 'finance/forecast.html', context, status=503)
        except OperationalError:
            context['error'] = 'Dữ liệu đang được cập nhật hoặc cơ sở dữ liệu đang bận. Chưa tạo kết quả mới; hãy thử lại.'
            return render(request, 'finance/forecast.html', context, status=409)
        return redirect(reverse('finance:forecast'))
    if valid and source['history_count'] >= CONFIG['minimum_months']:
        context['result'] = saved
        context['method_label'] = METHOD_LABELS[saved.method]
        context['selected_is_ml'] = saved.method.startswith('ridge_')
        context['comparisons'] = [
            {'method': item['method'], 'label': METHOD_LABELS[item['method']],
             'mae': Decimal(item['mae']), 'selected': item['method'] == saved.method}
            for item in saved.details.get('candidates', [])
        ]
        validation = saved.details.get('validation_months', [])
        if validation:
            context['validation_start'] = date.fromisoformat(validation[0])
            context['validation_end'] = date.fromisoformat(validation[-1])
    return render(request, 'finance/forecast.html', context)
