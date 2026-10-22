from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .forecast_history import review, ReviewChanged


@login_required
@require_GET
@never_cache
def history(request):
    try:
        context = review(request.user)
    except ReviewChanged as exc:
        return render(request, 'finance/forecast_history.html', {'error': str(exc)}, status=409)
    context['page_obj'] = Paginator(context.pop('rows'), 20).get_page(request.GET.get('page'))
    return render(request, 'finance/forecast_history.html', context)
