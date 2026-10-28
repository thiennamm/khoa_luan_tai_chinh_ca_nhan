from datetime import date
import re

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from . import recurring
from .financial_calendar import (CalendarMonthForm, actual_item, coverage_label, month_data,
    owned_rows, plans_for_month, plan_item)
from .services import recorded_totals


@login_required
@require_GET
@never_cache
def calendar_month(request):
    form = CalendarMonthForm({'month': request.GET.get('month', recurring.today().strftime('%Y-%m'))})
    show_empty = request.GET.get('show_empty') == '1'
    context = {'month_form': form, 'current_month': recurring.today().replace(day=1), 'show_empty': show_empty}
    valid = form.is_valid()
    if valid:
        context.update(month_data(request.user, form.cleaned_data['month']))
        context['mobile_days'] = [cell for cell in context['days'] if show_empty or cell['item_count'] > 0]
    return render(request, 'finance/financial_calendar.html', context, status=200 if valid else 400)


@login_required
@require_GET
@never_cache
def calendar_day(request, day):
    try:
        if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', day):
            raise ValueError
        selected = date.fromisoformat(day)
    except ValueError:
        raise Http404('Ngày lịch không hợp lệ.') from None
    today = recurring.today()
    month = selected.replace(day=1)
    rows = owned_rows(request.user).filter(date=selected).select_related('category', 'recurring_occurrence').order_by('-id')
    totals = recorded_totals(rows.values_list('kind', 'amount').iterator())
    page = Paginator(rows, 20).get_page(request.GET.get('page'))
    page.object_list = [actual_item(row, request.user, today) for row in page.object_list]
    plans = plans_for_month(request.user, month)
    planned = [plan_item(row) for row in plans.pop('pending_plans') if row['due_date'] == selected]
    plans_page = Paginator(planned, 20).get_page(request.GET.get('plans_page'))
    return render(request, 'finance/financial_calendar_day.html', {
        **totals, **plans, 'day': selected, 'month': month, 'today': today, 'future': selected > today,
        'show_empty': request.GET.get('show_empty') == '1',
        'page_obj': page, 'plans_page': plans_page, 'coverage': coverage_label(request.user, month)})
