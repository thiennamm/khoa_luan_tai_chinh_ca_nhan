from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .monthly_report import MonthlyReportForm, VIETNAM, report_data


@login_required
@require_GET
@never_cache
def monthly_report(request):
    params = request.GET.copy()
    if 'month' not in params:
        params['month'] = timezone.localdate(timezone=VIETNAM).strftime('%Y-%m')
    form = MonthlyReportForm(params)
    context = {'report_form': form}
    valid = form.is_valid()
    if valid:
        context.update(report_data(request.user, form.cleaned_data['month'], form.cleaned_data['include_details']))
    return render(request, 'finance/monthly_report.html', context, status=200 if valid else 400)
