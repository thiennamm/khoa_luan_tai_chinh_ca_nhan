from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import OperationalError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .models import SavingsGoal, SavingsEntry
from .savings_forms import SavingsGoalForm, SavingsEntryForm, OperationForm
from . import savings


def owned(user, pk):
    return get_object_or_404(SavingsGoal, pk=pk, user=user)


def apply(request, form, action, goal=None, entry_id=None, fields=()):
    if request.method != 'POST' or not form.is_valid():
        return None
    try:
        saved, repeated = savings.execute(request.user, form.cleaned_data['operation_token'], action,
            goal.pk if goal else None, entry_id, {key:form.cleaned_data[key] for key in fields})
    except ValidationError as exc:
        if hasattr(exc, 'message_dict'):
            for key, errors in exc.message_dict.items():
                form.add_error(key if key in form.fields else None, errors)
        else:
            form.add_error(None, exc)
    except savings.SavingsConflict as exc:
        form.add_error(None, str(exc))
    except OperationalError as exc:
        if 'locked' not in str(exc).lower():
            raise
        form.add_error(None, 'Một thao tác khác đang xử lý. Hãy thử lại với biểu mẫu này; không cần bấm liên tục.')
    else:
        messages.success(request, 'Thao tác này đã được ghi nhận trước đó; không tạo thêm bản ghi.' if repeated
            else 'Đã cập nhật mục tiêu. Đây là phân bổ tự ghi nhận, không tạo giao dịch thu/chi.')
        return redirect('finance:savings_detail', pk=saved.pk)
    return None


@login_required
@require_http_methods(['GET'])
@never_cache
def goal_list(request):
    return render(request, 'finance/savings_list.html', {
        'page_obj': Paginator(savings.summaries(request.user), 12).get_page(request.GET.get('page'))})


@login_required
@require_http_methods(['GET'])
@never_cache
def detail(request, pk):
    goal = owned(request.user, pk)
    return render(request, 'finance/savings_detail.html', {'goal':goal, 'item':savings.summary(goal),
        'page_obj':Paginator(goal.entries.all(), 20).get_page(request.GET.get('page'))})


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def goal_edit(request, pk=None):
    goal = owned(request.user, pk) if pk else None
    action = 'goal_edit' if goal else 'goal_create'
    form = SavingsGoalForm(request.POST if request.method == 'POST' else None, user=request.user,
        instance=goal, initial={'operation_token':savings.issue(request.user, action, goal)})
    result = apply(request, form, action, goal, fields=('name','amount','start_date','due_date','note'))
    return result or render(request, 'finance/savings_form.html', {
        'form':form, 'goal':goal, 'title':'Sửa mục tiêu' if goal else 'Tạo mục tiêu tiết kiệm', 'entry_form':False})


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def goal_status(request, pk, action):
    if action not in ('archive','reopen'):
        raise Http404
    goal = owned(request.user, pk)
    form = OperationForm(request.POST if request.method == 'POST' else None,
        initial={'operation_token':savings.issue(request.user, action, goal)})
    result = apply(request, form, action, goal)
    return result or render(request, 'finance/savings_confirm.html', {'form':form, 'goal':goal,
        'title':'Lưu trữ mục tiêu' if action == 'archive' else 'Mở lại mục tiêu',
        'explanation':'Lịch sử được giữ nguyên. Khi lưu trữ, không thể thêm, sửa hoặc xóa khoản phân bổ.'
            if action == 'archive' else 'Bạn có thể tiếp tục ghi nhận hoặc sửa các khoản phân bổ sau khi mở lại.'})


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def entry_edit(request, pk, entry_id=None):
    goal = owned(request.user, pk)
    entry = get_object_or_404(SavingsEntry, goal=goal, pk=entry_id) if entry_id else None
    action = 'entry_edit' if entry else 'entry_create'
    form = SavingsEntryForm(request.POST if request.method == 'POST' else None, goal=goal, instance=entry,
        initial={'operation_token':savings.issue(request.user, action, goal, entry)})
    result = apply(request, form, action, goal, entry_id, fields=('kind','amount','date','note'))
    return result or render(request, 'finance/savings_form.html', {'form':form, 'goal':goal,
        'title':'Sửa khoản phân bổ' if entry else 'Ghi nhận khoản phân bổ', 'entry_form':True})


@login_required
@require_http_methods(['GET','POST'])
@never_cache
def entry_delete(request, pk, entry_id):
    goal = owned(request.user, pk)
    entry = SavingsEntry.objects.filter(goal=goal, pk=entry_id).first()
    if entry is None and request.method == 'GET':
        raise Http404
    form = OperationForm(request.POST if request.method == 'POST' else None,
        initial={'operation_token':savings.issue(request.user, 'entry_delete', goal, entry)})
    result = apply(request, form, 'entry_delete', goal, entry_id)
    return result or render(request, 'finance/savings_confirm.html', {'form':form, 'goal':goal,
        'entry':entry, 'title':'Xóa khoản phân bổ',
        'explanation':'Bản ghi này sẽ bị xóa khi bạn xác nhận. Hệ thống kiểm lại toàn bộ lịch sử và từ chối nếu có thời điểm số tích lũy âm.'})
