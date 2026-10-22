from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, OperationalError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from . import recurring
from .forms import MonthForm
from .models import Category, RecurringRule, RecurringOccurrence
from .recurring_forms import RecurringActionForm, RecurringConfirmationForm, RecurringRuleForm

STATES = [('all', 'Tất cả'), ('due', 'Đến hạn / quá hạn'), ('upcoming', 'Sắp đến hạn'),
    ('recorded', 'Đã ghi nhận'), ('skipped', 'Đã bỏ qua'), ('deleted', 'Giao dịch đã xóa')]


@login_required
@require_http_methods(['GET'])
def recurring_list(request):
    month_form = MonthForm({'month': request.GET.get('month', recurring.today().strftime('%Y-%m'))})
    rows = []
    state = request.GET.get('state', 'all')
    if month_form.is_valid():
        month = month_form.cleaned_data['month']
        first, last = recurring.window()
        if not first <= month <= last:
            month_form.add_error('month', 'Chọn trong 12 tháng đến tháng hiện tại hoặc xem trước tháng sau.')
        elif state not in dict(STATES):
            month_form.add_error(None, 'Trạng thái không hợp lệ.')
        else:
            rows = recurring.monthly_items(request.user, month)
            if state != 'all':
                rows = [row for row in rows if row['state'] == state]
    params = request.GET.copy()
    params.pop('page', None); params.pop('rules_page', None)
    rules_page = Paginator(RecurringRule.objects.filter(user=request.user).select_related('category')
        .prefetch_related('revisions'), 20).get_page(request.GET.get('rules_page'))
    for rule in rules_page:
        rule.display_status = recurring.rule_status(rule)
    return render(request, 'finance/recurring_list.html', {
        'month_form': month_form, 'state': state, 'states': STATES, 'filter_query': params.urlencode(),
        'page_obj': Paginator(rows, 20).get_page(request.GET.get('page')),
        'rules_page': rules_page,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def rule_edit(request, pk=None):
    rule = get_object_or_404(RecurringRule, pk=pk, user=request.user) if pk else None
    form = RecurringRuleForm(request.POST if request.method == 'POST' else None,
        instance=rule, user=request.user, initial={} if rule else {'start_month': recurring.today().replace(day=1)})
    if request.method == 'POST' and form.is_valid():
        try:
            recurring.save_rule(form, request.user)
        except (ValidationError, IntegrityError, OperationalError, recurring.RecurringConflict):
            form.add_error(None, 'Chưa thể lưu quy tắc. Kiểm tra danh mục hoặc thử lại nếu dữ liệu đang được cập nhật.')
        else:
            messages.success(request, 'Đã lưu quy tắc. Thay đổi thông tin có hiệu lực từ tháng sau.' if rule else 'Đã tạo quy tắc hàng tháng. Chưa tạo giao dịch thực tế.')
            return redirect('finance:recurring_list')
    return render(request, 'finance/recurring_rule_form.html', {'form': form, 'editing': rule is not None})


@login_required
@require_http_methods(['GET', 'POST'])
def rule_status(request, pk, action):
    rule = get_object_or_404(RecurringRule, pk=pk, user=request.user)
    if action not in ('pause', 'resume'):
        from django.http import Http404
        raise Http404
    form = RecurringActionForm(request.POST if request.method == 'POST' else None)
    form.fields['confirm'].label = 'Tôi xác nhận thay đổi trạng thái quy tắc này.'
    if request.method == 'POST' and form.is_valid():
        try:
            recurring.set_active(request.user, rule.pk, action == 'resume')
        except (ValidationError, IntegrityError, OperationalError, recurring.RecurringConflict):
            form.add_error(None, 'Chưa thể đổi trạng thái. Vui lòng thử lại.')
        else:
            messages.success(request, 'Đã tạm dừng từ tháng hiện tại.' if action == 'pause' else 'Đã lên lịch kích hoạt lại từ tháng sau. Không tạo bù các tháng đã dừng.')
            return redirect('finance:recurring_list')
    return render(request, 'finance/recurring_action.html', {'form': form, 'rule': rule,
        'action_title': 'Tạm dừng quy tắc' if action == 'pause' else 'Kích hoạt lại quy tắc',
        'explanation': 'Dừng các kỳ chưa từng xử lý từ tháng hiện tại. Các tháng trước, lịch sử và kỳ đã mở lại thủ công giữ nguyên; kỳ đã mở lại vẫn có thể được xử lý theo snapshot.' if action == 'pause' else 'Bắt đầu lại từ tháng sau. Không tự tạo bù các tháng đã tạm dừng.'})


@login_required
@require_http_methods(['GET', 'POST'])
def occurrence_action(request, pk, year, month, action):
    from django.http import Http404
    rule = get_object_or_404(RecurringRule.objects.prefetch_related('revisions'), pk=pk, user=request.user)
    try:
        period = date(year, month, 1)
        recurring.validate_month(period)
    except (ValueError, recurring.RecurringConflict):
        raise Http404 from None
    if action not in ('record', 'skip', 'reopen'):
        raise Http404
    occurrence = RecurringOccurrence.objects.filter(rule=rule, month=period, user=request.user).select_related('transaction').first()
    row = recurring.item(rule, period, occurrence)
    if row is None:
        raise Http404
    if action == 'record':
        cat = Category.objects.filter(pk=row['snapshot']['category_id'], user=request.user,
            kind=row['snapshot']['kind']).first()
        form = RecurringConfirmationForm(request.POST if request.method == 'POST' else None,
            user=request.user, expected_kind=row['snapshot']['kind'], initial={
                'amount': row['amount'], 'category': cat,
                'description': row['snapshot']['name']})
    else:
        form = RecurringActionForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            result = recurring.process(request.user, rule.pk, period, action, form if action == 'record' else None)
        except (ValidationError, IntegrityError, OperationalError, Category.DoesNotExist, recurring.RecurringConflict):
            form.add_error(None, 'Kỳ đã thay đổi hoặc dữ liệu chưa hợp lệ. Hãy tải lại trang; không tự ghi nhận lại kỳ đã xử lý.')
        else:
            messages.success(request, {'record': 'Đã ghi nhận kỳ bằng giao dịch thực tế.', 'skip': 'Đã bỏ qua kỳ; không tạo giao dịch.', 'reopen': 'Đã mở lại kỳ. Chưa tạo giao dịch mới.'}[action])
            if result.transaction_id:
                return redirect('finance:transaction_detail', pk=result.transaction_id)
            return redirect('finance:recurring_list')
    return render(request, 'finance/recurring_confirm.html', {'form': form, 'item': row, 'action': action,
        'events': occurrence.events.all() if occurrence else []})


@login_required
@require_http_methods(['GET'])
def rule_history(request, pk):
    rule = get_object_or_404(RecurringRule, pk=pk, user=request.user)
    page = Paginator(rule.occurrences.filter(user=request.user).select_related('transaction').order_by('-month', '-pk'), 20).get_page(request.GET.get('page'))
    page.object_list = [recurring.item(rule, occurrence.month, occurrence) for occurrence in page.object_list]
    return render(request, 'finance/recurring_history.html', {'rule': rule,
        'page_obj': page})
