"""Read-only calendar of recorded transactions and existing monthly plans."""
from calendar import monthrange
from datetime import date
from itertools import groupby
import re

from django import forms
from django.db.models import F, Window
from django.db.models.functions import RowNumber

from . import recurring
from .forms import MonthForm
from .models import Transaction, MonthlyCoverage
from .services import recorded_totals

PREVIEW_LIMIT = 2


class CalendarMonthForm(MonthForm):
    def clean_month(self):
        if not re.fullmatch(r'[0-9]{4}-(0[1-9]|1[0-2])', self.data.get('month', '')):
            raise forms.ValidationError('Chọn tháng hợp lệ theo dạng YYYY-MM.')
        return self.cleaned_data['month']


def month_bounds(month):
    return month, month.replace(day=monthrange(month.year, month.month)[1])


def owned_rows(user):
    return Transaction.objects.filter(user=user, category__user=user)


def coverage_label(user, month):
    value = MonthlyCoverage.objects.filter(user=user, month=month).values_list('status', flat=True).first()
    return MonthlyCoverage.Status(value or MonthlyCoverage.Status.UNKNOWN).label


def plans_for_month(user, month):
    first, last = recurring.window()
    available = first <= month <= last
    rows = recurring.monthly_items(user, month) if available else []
    # Processed/deleted periods are never resurrected as unpaid estimates.
    pending = [row for row in rows if row['state'] in ('due', 'upcoming')]
    return {'plans_available': available, 'plan_window_start': first, 'plan_window_end': last,
        'pending_plans': pending, 'recorded_periods': sum(row['state'] == 'recorded' for row in rows),
        'skipped_periods': sum(row['state'] == 'skipped' for row in rows),
        'deleted_periods': sum(row['state'] == 'deleted' for row in rows)}


def actual_item(row, user, today):
    occurrence = getattr(row, 'recurring_occurrence', None)
    # Do not surface an inconsistent cross-account occurrence even if inserted
    # outside the supported write services. Never dereference its rule/category.
    linked = occurrence if occurrence and occurrence.user_id == user.pk else None
    return {'id': row.pk, 'date': row.date, 'kind': row.kind, 'kind_label': row.get_kind_display(),
        'amount': row.amount, 'description': row.description, 'category': row.category.name,
        'future': row.date > today, 'planned': False,
        'period_month': linked.month if linked else None, 'due_date': linked.due_date if linked else None}


def plan_item(row):
    return {'planned': True, 'rule_id': row['rule'].pk, 'month': row['month'], 'date': row['due_date'],
        'kind': row['snapshot']['kind'], 'kind_label': 'Thu' if row['snapshot']['kind'] == 'income' else 'Chi',
        'amount': row['amount'], 'description': row['snapshot']['name'],
        'category': row['snapshot']['category_name'], 'can_process': row['can_process'],
        'state_label': row['state_label']}


def month_data(user, month):
    today = recurring.today()
    start, end = month_bounds(month)
    rows = owned_rows(user).filter(date__gte=start, date__lte=end)
    days = {}
    # Only the selected month, no descriptions/models loaded for the full scan.
    for day, values in groupby(rows.order_by('date').values_list('date', 'kind', 'amount').iterator(), key=lambda r:r[0]):
        entries = list(values)
        days[day] = {**recorded_totals((kind, amount) for _, kind, amount in entries), 'actual_count': len(entries),
            'has_income': any(kind == 'income' for _, kind, _ in entries),
            'has_expense': any(kind == 'expense' for _, kind, _ in entries)}
    totals = recorded_totals((kind, data[kind]) for data in days.values() for kind in ('income', 'expense'))
    actual_count = sum(data['actual_count'] for data in days.values())
    # Limit in SQL to <= 2 per date, not all monthly descriptions then Python slice.
    previews = rows.annotate(calendar_rank=Window(RowNumber(), partition_by=[F('date')],
        order_by=F('id').desc())).filter(calendar_rank__lte=PREVIEW_LIMIT)
    previews = previews.select_related('category', 'recurring_occurrence').order_by('date', '-id')
    preview_by_day = {}
    for row in previews:
        preview_by_day.setdefault(row.date, []).append(actual_item(row, user, today))
    plans = plans_for_month(user, month)
    planned_by_day = {}
    for row in plans['pending_plans']:
        planned_by_day.setdefault(row['due_date'], []).append(plan_item(row))
    cells = []
    offset = month.weekday()
    total_cells = ((offset + end.day + 6) // 7) * 7
    for index in range(total_cells):
        ordinal = month.toordinal() - offset + index
        day = date.fromordinal(ordinal) if 1 <= ordinal <= date.max.toordinal() else None
        inside = day is not None and start <= day <= end
        cell = {'day': day, 'inside': inside, 'today': day == today, 'future': day is not None and day > today}
        if inside:
            data = days.get(day, {**recorded_totals([]), 'actual_count': 0, 'has_income': False, 'has_expense': False})
            estimated = planned_by_day.get(day, [])
            items = (preview_by_day.get(day, []) + estimated[:PREVIEW_LIMIT])[:PREVIEW_LIMIT]
            count = data['actual_count'] + len(estimated)
            cell.update(data, items=items, plan_count=len(estimated), item_count=count,
                more=count > len(items), more_count=count - len(items))
        cells.append(cell)
    context = {**totals, **plans, 'actual_count': actual_count, 'plan_count': len(plans['pending_plans']),
        'weeks': [cells[i:i+7] for i in range(0, len(cells), 7)], 'days': [c for c in cells if c['inside']],
        'today': today, 'month': month, 'coverage': coverage_label(user, month)}
    # Full plan list is an implementation detail; templates only receive bounded previews.
    context.pop('pending_plans')
    for name, shift in [('previous_month', -1), ('next_month', 1)]:
        try: context[name] = recurring.shift(month, shift)
        except ValueError: context[name] = None
    return context
