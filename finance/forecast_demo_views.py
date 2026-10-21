from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from . import forecast_demo
from .forecast_config import METHOD_LABELS
from .forecast_math import ForecastFailure


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def demo(request):
    source = forecast_demo.scenario()
    error = None
    if request.method == 'POST':
        try:
            forecast_demo.run_demo(source)
        except ForecastFailure as exc:
            error = str(exc)
        else:
            return redirect('finance:forecast_demo')
    result = None if error else forecast_demo.cached_result(source)
    comparisons = [dict(label=METHOD_LABELS[row['method']], mae=Decimal(row['mae']),
                        raw_mae=row['mae'], selected=row['method'] == result['method'])
                   for row in result['candidates']] if result else []
    return render(request, 'finance/forecast_demo.html', {
        'source': source, 'result': result, 'error': error,
        'method_label': METHOD_LABELS[result['method']] if result else None,
        'selected_is_ml': bool(result and result['method'].startswith('ridge_')),
        'comparisons': comparisons, 'chart': forecast_demo.chart(source, result),
    }, status=503 if error else 200)
