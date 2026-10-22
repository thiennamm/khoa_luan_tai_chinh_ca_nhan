from datetime import date
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from .classification_modes import suggest_label, ModelUnavailable
from .classification_labels import LABELS, compatible_kind
from .forms import SuggestionForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.db import transaction, IntegrityError
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .forms import CategoryForm, MonthForm, SignUpForm, TransactionForm
from .models import Category, Transaction
from .services import monthly_totals
from .transaction_filters import TransactionFilterForm, apply_filters, filtered_totals
from .statistics import StatisticsSpanForm, financial_statistics
from .budgets import monthly_budgets


@login_required
@require_http_methods(['POST'])
@never_cache
def category_suggestion(request):
    form = SuggestionForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'status': 'invalid', 'message': 'Nhập mô tả tối đa 500 ký tự, chọn chế độ và loại thu/chi hợp lệ.'}, status=400)
    try:
        label = suggest_label(form.cleaned_data['description'], mode=form.cleaned_data['mode'])
    except ModelUnavailable:
        return JsonResponse({'status': 'unavailable', 'message': 'Không có gợi ý: mô hình đã chọn tạm không sẵn sàng. Bạn vẫn có thể nhập và lưu giao dịch thủ công.'}, status=503)
    if label is None:
        return JsonResponse({'status': 'no_suggestion', 'message': 'Chưa có gợi ý: mô tả trống hoặc không có đặc trưng phù hợp. Hãy tự chọn danh mục.'})
    payload = {'status': 'suggestion', 'label': label, 'label_display': LABELS[label], 'categories': []}
    if label == 'Transfer':
        payload.update(status='review', message='Có thể là chuyển khoản. Cần xem lại bản chất giao dịch; không tự coi là thu nhập hay chi tiêu. Không áp dụng gợi ý này vào danh mục thu/chi.')
    elif compatible_kind(label) != form.cleaned_data['kind']:
        payload.update(status='review', message='Nhãn dự đoán khác loại thu/chi bạn đang chọn. Hãy xem lại và tự chọn danh mục; loại giao dịch được giữ nguyên.')
    else:
        payload['categories'] = list(Category.objects.filter(
            user=request.user, kind=form.cleaned_data['kind'], canonical_label=label,
        ).values('id', 'name'))
        payload['message'] = ('Chọn danh mục rồi bấm Áp dụng. Giao dịch chỉ được lưu khi bạn bấm Lưu giao dịch.'
                              if payload['categories'] else 'Chưa có danh mục được ánh xạ với nhãn này. Bạn có thể sửa ánh xạ trong Danh mục hoặc tự chọn danh mục khi nhập.')
    return JsonResponse(payload)


def month_context(request):
    today = timezone.localdate()
    form = MonthForm({"month": request.GET.get("month", today.strftime("%Y-%m"))})
    valid = form.is_valid()
    start = form.cleaned_data["month"] if valid else today.replace(day=1)
    if start.year == 9999 and start.month == 12:
        form.add_error("month", "Vui lòng chọn tháng trước tháng 12/9999.")
        valid = False
        start = today.replace(day=1)
    end = date(start.year + (start.month == 12), start.month % 12 + 1, 1)
    return {"month_form": form, "month": start.strftime("%Y-%m"),
            "month_label": start.strftime("%m/%Y"), "start": start, "end": end, "month_valid": valid}


@require_http_methods(["GET", "POST"])
def signup(request):
    if request.user.is_authenticated:
        return redirect("finance:dashboard")
    form = SignUpForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Đăng ký thành công. Vui lòng đăng nhập để tiếp tục.")
        return redirect("login")
    return render(request, "registration/signup.html", {"form": form})


@login_required
@require_http_methods(["GET"])
def dashboard(request):
    context = month_context(request)
    rows = Transaction.objects.filter(user=request.user, date__gte=context["start"], date__lt=context["end"])
    context['recent_transactions'] = rows.select_related('category')[:5]
    span_form = StatisticsSpanForm({'span': request.GET.get('span', '6')})
    context['statistics_span_form'] = span_form
    if span_form.is_valid():
        context.update(financial_statistics(request.user, context['start'], span_form.cleaned_data['span']))
        selected = context['monthly_statistics'][-1]
        context.update({key: selected[key] for key in ['income', 'expense', 'balance']})
        context['transaction_count'] = selected['count']
    else:
        context.update(monthly_totals(request.user, context['start'], context['end']))
        context['transaction_count'] = rows.count()
    context.update(monthly_budgets(request.user, context['start']))
    return render(request, "finance/dashboard.html", context)


@login_required
@require_http_methods(["GET"])
def transaction_list(request):
    form = TransactionFilterForm(request.GET, user=request.user)
    valid = form.is_valid()
    rows = Transaction.objects.filter(user=request.user)
    rows = apply_filters(rows, form.cleaned_data) if valid else rows.none()
    params = form.data.copy()
    inactive = {'start', 'end'} if form.data.get('period') == 'month' else {'month'}
    for name in list(params):
        if name not in form.fields or name in inactive:
            params.pop(name, None)
    context = {'filter_form': form, 'filters_valid': valid, 'filter_query': params.urlencode(),
               'page_obj': Paginator(rows.select_related('category'), 20).get_page(request.GET.get('page'))}
    context.update(filtered_totals(rows))
    return render(request, "finance/transaction_list.html", context)


@login_required
@require_http_methods(["GET"])
def transaction_detail(request, pk):
    row = get_object_or_404(Transaction.objects.select_related("category"), pk=pk, user=request.user)
    return render(request, "finance/transaction_detail.html", {"transaction": row})


@login_required
@require_http_methods(["GET", "POST"])
def transaction_edit(request, pk=None):
    row = get_object_or_404(Transaction, pk=pk, user=request.user) if pk is not None else None
    form = TransactionForm(request.POST if request.method == "POST" else None, instance=row, user=request.user)
    if request.method == "POST" and form.is_valid():
        saved = form.save()
        messages.success(request, "Đã cập nhật giao dịch." if row else "Đã thêm giao dịch.")
        return redirect("finance:transaction_detail", pk=saved.pk)
    categories = Category.objects.filter(user=request.user)
    return render(request, "finance/transaction_form.html", {
        "form": form, "editing": row is not None, "has_categories": categories.exists(),
        "category_kinds": {str(c.pk): c.kind for c in categories},
    })


@login_required
@require_http_methods(["GET", "POST"])
def transaction_delete(request, pk):
    row = get_object_or_404(Transaction.objects.select_related("category"), pk=pk, user=request.user)
    if request.method == "POST":
        row.delete()
        messages.success(request, "Đã xóa giao dịch.")
        return redirect("finance:transaction_list")
    return render(request, "finance/confirm_delete.html", {"object": row, "object_type": "giao dịch", "cancel_url": "finance:transaction_list"})


@login_required
@require_http_methods(["GET"])
def category_list(request):
    categories = Category.objects.filter(user=request.user).annotate(transaction_count=Count("transactions"))
    return render(request, "finance/category_list.html", {"categories": categories})


@login_required
@require_http_methods(["GET", "POST"])
def category_edit(request, pk=None):
    category = get_object_or_404(Category, pk=pk, user=request.user) if pk is not None else None
    form = CategoryForm(request.POST if request.method == "POST" else None, instance=category, user=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                form.save()
        except (ValidationError, IntegrityError):
            form.add_error(None, 'Không thể lưu danh mục. Kiểm tra ngân sách/giao dịch liên quan hoặc tên bị trùng rồi thử lại.')
        else:
            messages.success(request, "Đã lưu danh mục.")
            return redirect("finance:category_list")
    return render(request, "finance/category_form.html", {"form": form, "editing": category is not None})


@login_required
@require_http_methods(["GET", "POST"])
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    if request.method == "POST":
        try:
            category.delete()
        except ProtectedError:
            messages.error(request, "Không thể xóa danh mục đang có giao dịch hoặc ngân sách. Hãy xử lý các mục liên quan trước.")
        else:
            messages.success(request, "Đã xóa danh mục.")
        return redirect("finance:category_list")
    return render(request, "finance/confirm_delete.html", {
        "object": category, "object_type": "danh mục", "cancel_url": "finance:category_list",
        "protected": category.transactions.exists() or category.budgets.exists(),
    })
