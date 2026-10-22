"""Ngân sách chỉ đối chiếu expense đã ghi; không thay coverage/dự báo."""
from calendar import monthrange
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from .models import Budget, Transaction, MonthlyCoverage


def budget_progress(budget, spent):
    # So sánh trước làm tròn để 79,999% không bị gọi là gần chạm.
    status = ('over' if spent > budget.amount else 'reached' if spent == budget.amount
              else 'near' if spent * 100 >= budget.amount * 80 else 'within')
    labels = {'within': 'Trong hạn mức', 'near': 'Gần chạm hạn mức',
              'reached': 'Đã chạm hạn mức', 'over': 'Vượt hạn mức'}
    percent = spent * Decimal(100) / budget.amount
    return {'budget': budget, 'spent': spent, 'remaining': max(budget.amount-spent, Decimal(0)),
            'over': max(spent-budget.amount, Decimal(0)), 'status': status, 'status_label': labels[status],
            'percent': percent.quantize(Decimal('.01'), rounding=ROUND_HALF_UP),
            'width': format(min(Decimal(100), percent).quantize(Decimal('.01'), rounding=ROUND_HALF_UP), 'f')}


def monthly_budgets(user, month):
    if month.day != 1:
        raise ValueError('Tháng không hợp lệ')
    end = date(month.year, month.month, monthrange(month.year, month.month)[1])
    total = Decimal(0)
    by_category = {}
    for category_id, amount in Transaction.objects.filter(user=user, category__user=user,
            kind='expense', date__gte=month, date__lte=end).order_by().values_list('category_id', 'amount').iterator():
        total += amount
        by_category[category_id] = by_category.get(category_id, Decimal(0)) + amount
    budgets = Budget.objects.filter(user=user, month=month).select_related('category').order_by('category__name', 'pk')
    summary = None
    categories = []
    for budget in budgets:
        if budget.category_id is None:
            summary = budget_progress(budget, total)
        elif budget.category.user_id == user.pk and budget.category.kind == 'expense':
            categories.append(budget_progress(budget, by_category.get(budget.category_id, Decimal(0))))
    coverage = MonthlyCoverage.objects.filter(user=user, month=month).values_list('status', flat=True).first()
    status = coverage or MonthlyCoverage.Status.UNKNOWN
    return {'total_budget': summary, 'category_budgets': categories, 'recorded_expense': total,
            'budget_coverage': MonthlyCoverage.Status(status).label, 'budget_month': month}
