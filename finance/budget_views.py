from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .models import Budget
from .budget_forms import BudgetForm
from .budgets import monthly_budgets
from .views import month_context


@login_required
@require_http_methods(['GET'])
@never_cache
def budget_list(request):
    context = month_context(request)
    context.update(monthly_budgets(request.user, context['start']))
    return render(request, 'finance/budget_list.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
@never_cache
def budget_edit(request, pk=None):
    budget = get_object_or_404(Budget, pk=pk, user=request.user) if pk is not None else None
    initial = {'month': month_context(request)['start']} if budget is None else None
    form = BudgetForm(request.POST if request.method == 'POST' else None,
                      instance=budget, initial=initial, user=request.user)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                saved = form.save()
        except (IntegrityError, ValidationError):
            form.add_error(None, 'Không thể lưu: ngân sách đã tồn tại hoặc danh mục vừa thay đổi. Hãy kiểm tra và thử lại.')
        else:
            messages.success(request, 'Đã cập nhật ngân sách.' if budget else 'Đã tạo ngân sách.')
            return redirect(reverse('finance:budget_list') + '?month=' + saved.month.strftime('%Y-%m'))
    return render(request, 'finance/budget_form.html', {'form': form, 'editing': budget is not None})


@login_required
@require_http_methods(['GET', 'POST'])
@never_cache
def budget_delete(request, pk):
    budget = get_object_or_404(Budget.objects.select_related('category'), pk=pk, user=request.user)
    if request.method == 'POST':
        month = budget.month.strftime('%Y-%m')
        budget.delete()
        messages.success(request, 'Đã xóa ngân sách. Các giao dịch được giữ nguyên.')
        return redirect(reverse('finance:budget_list') + '?month=' + month)
    return render(request, 'finance/confirm_delete.html', {'object': budget,
        'object_type': 'ngân sách', 'cancel_url': 'finance:budget_list'})
