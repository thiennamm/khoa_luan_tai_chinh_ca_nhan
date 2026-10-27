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
from django.db.models import Count, Q
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
from . import classification_feedback as feedback_service
from .recurring import dashboard_items, today as vietnam_today
from .models import ClassificationFeedback, ClassificationSuggestion
from .savings import summaries as savings_summaries
from .category_defaults import getting_started
from .category_mapping_help import label_guide, mapping_peers, RENAME_HELP
from . import similar_transactions
from .forms import SimilarTransactionForm


def suggestion_source(request):
    value = request.POST.get('transaction_id', '')
    if not value:
        return None
    try:
        key = int(value)
        if not 0 < key <= 9223372036854775807:
            raise ValueError
        return Transaction.objects.get(pk=key, user=request.user)
    except (ValueError, OverflowError, Transaction.DoesNotExist):
        raise feedback_service.InvalidSuggestion from None


@login_required
@require_http_methods(['POST'])
@never_cache
def suggestion_action(request):
    try:
        token = request.POST.get('suggestion_id', '')
        if request.POST.get('action') == 'revoke':
            receipt = feedback_service.owned_receipt(request.user, token)
            ClassificationSuggestion.objects.filter(pk=receipt.pk, consumed_at__isnull=True).update(revoked_at=timezone.now())
            return JsonResponse({'status': 'revoked'})
        form = SuggestionForm(request.POST)
        if request.POST.get('action') != 'apply' or not form.is_valid():
            raise feedback_service.InvalidSuggestion
        source = suggestion_source(request)
        category = feedback_service.apply_receipt(request.user, token, form.cleaned_data,
            source.pk if source else None, request.POST.get('category', ''))
    except feedback_service.InvalidSuggestion:
        return JsonResponse({'status': 'invalid', 'message': 'Gợi ý không còn hợp lệ. Hãy yêu cầu gợi ý lại hoặc chọn danh mục thủ công.'}, status=400)
    return JsonResponse({'status': 'applied', 'category_id': category.pk})


@login_required
@require_http_methods(['GET'])
@never_cache
def classification_feedback_list(request):
    rows = ClassificationFeedback.objects.filter(user=request.user)
    counts = rows.aggregate(total=Count('pk'), same=Count('pk', filter=Q(same_label=True)),
        different=Count('pk', filter=Q(same_label=False)), applied=Count('pk', filter=Q(applied=True)))
    return render(request, 'finance/classification_feedback.html', {
        **counts,
        'page_obj': Paginator(rows, 20).get_page(request.GET.get('page')),
    })


@login_required
@require_http_methods(['POST'])
@never_cache
def category_suggestion(request):
    form = SuggestionForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'status': 'invalid', 'message': 'Nhập mô tả tối đa 500 ký tự, chọn chế độ và loại thu/chi hợp lệ.'}, status=400)
    try:
        source = suggestion_source(request)
    except feedback_service.InvalidSuggestion:
        return JsonResponse({'status': 'invalid', 'message': 'Giao dịch không hợp lệ.'}, status=400)
    try:
        label = suggest_label(form.cleaned_data['description'], mode=form.cleaned_data['mode'])
    except ModelUnavailable:
        return JsonResponse({'status': 'unavailable', 'message': 'Không có gợi ý: mô hình đã chọn tạm không sẵn sàng. Bạn vẫn có thể nhập và lưu giao dịch thủ công.'}, status=503)
    if label is None:
        return JsonResponse({'status': 'no_suggestion', 'message': 'Chưa có gợi ý: mô tả trống hoặc không có đặc trưng phù hợp. Hãy tự chọn danh mục.'})
    payload = {'status': 'suggestion', 'label': label, 'label_display': LABELS[label], 'categories': []}
    receipt = feedback_service.issue(request.user, form.cleaned_data, label, source)
    payload['suggestion_id'] = str(receipt.pk)
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
    context.update(dashboard_items(request.user))
    context['savings_goals'] = [item for item in savings_summaries(request.user) if item['state'] == 'active'][:3]
    context['getting_started'] = getting_started(request.user)
    return render(request, "finance/dashboard.html", context)


@login_required
@require_http_methods(["GET"])
def transaction_list(request):
    form = TransactionFilterForm(request.GET, user=request.user)
    valid = form.is_valid()
    rows = Transaction.objects.filter(user=request.user)
    has_transactions = rows.exists()
    rows = apply_filters(rows, form.cleaned_data) if valid else rows.none()
    params = form.data.copy()
    inactive = {'start', 'end'} if form.data.get('period') == 'month' else {'month'}
    for name in list(params):
        if name not in form.fields or name in inactive:
            params.pop(name, None)
    context = {'filter_form': form, 'filters_valid': valid, 'filter_query': params.urlencode(),
               'has_transactions': has_transactions,
               'page_obj': Paginator(rows.select_related('category'), 20).get_page(request.GET.get('page'))}
    context.update(filtered_totals(rows))
    return render(request, "finance/transaction_list.html", context)


@login_required
@require_http_methods(["GET"])
def transaction_detail(request, pk):
    row = get_object_or_404(Transaction.objects.select_related("category"), pk=pk, user=request.user)
    return render(request, "finance/transaction_detail.html", {"transaction": row, 'future_date': row.date > vietnam_today()})


@login_required
@require_http_methods(["GET", "POST"])
def transaction_edit(request, pk=None, *, similar=False, initial=None, category_needs_review=False):
    row = get_object_or_404(Transaction, pk=pk, user=request.user) if pk is not None else None
    form_class = SimilarTransactionForm if similar else TransactionForm
    form = form_class(request.POST if request.method == "POST" else None, instance=row, user=request.user, initial=initial)
    suggestion_id = request.POST.get('suggestion_id', '') if request.method == 'POST' else ''
    suggestion_mode = request.POST.get('suggestion_mode', 'vi')
    if request.method == "POST" and form.is_valid():
        try:
            if similar:
                saved, repeated = similar_transactions.save(form, request.user,
                    form.cleaned_data['similar_operation'], suggestion_id, suggestion_mode)
            else:
                saved = feedback_service.save_with_feedback(form, request.user, suggestion_id, suggestion_mode)
                repeated = False
        except similar_transactions.SimilarConflict as exc:
            form.add_error(None, str(exc))
        except feedback_service.InvalidSuggestion:
            suggestion_id = ''
            form.add_error(None, 'Gợi ý không còn hợp lệ. Hãy yêu cầu gợi ý lại, hoặc kiểm tra danh mục và bấm Lưu lần nữa để lưu thủ công không ghi phản hồi.')
        except (ValidationError, IntegrityError, Category.DoesNotExist):
            form.add_error(None, 'Không thể lưu giao dịch. Hãy kiểm tra lại danh mục và dữ liệu rồi thử lại.')
        else:
            messages.success(request, 'Thao tác này đã được lưu trước đó; không tạo thêm giao dịch.' if repeated
                else "Đã cập nhật giao dịch." if row else "Đã thêm giao dịch.")
            return redirect("finance:transaction_detail", pk=saved.pk)
    categories = Category.objects.filter(user=request.user)
    return render(request, "finance/transaction_form.html", {
        "form": form, "editing": row is not None, "has_categories": categories.exists(),
        "category_kinds": {str(c.pk): c.kind for c in categories},
        'suggestion_id': suggestion_id, 'suggestion_mode': suggestion_mode,
        'source_transaction_id': pk or '',
        'similar': similar, 'category_needs_review': category_needs_review,
    })


@login_required
@require_http_methods(['GET'])
@never_cache
def transaction_duplicate(request, pk):
    source = get_object_or_404(Transaction, pk=pk, user=request.user)
    initial, needs_review = similar_transactions.initial_data(source, request.user)
    return transaction_edit(request, similar=True, initial=initial, category_needs_review=needs_review)


@login_required
@require_http_methods(['POST'])
@never_cache
def transaction_duplicate_save(request):
    # No source lookup here: an open form remains independent of source edits/deletion.
    return transaction_edit(request, similar=True)


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
    has_transactions = category is not None and category.transactions.exists()
    form = CategoryForm(request.POST if request.method == "POST" else None, instance=category, user=request.user)
    peers = mapping_peers(request.user, category.pk if category else None)
    linked_names = peers.get(form['kind'].value(), {}).get(form['canonical_label'].value(), [])
    if request.method == "POST" and form.is_valid():
        if request.POST.get('action') == 'preview_mapping':
            return render(request, 'finance/category_form.html', {
                'form': form, 'editing': category is not None, 'has_transactions': has_transactions,
                'rename_help': RENAME_HELP, 'label_guide': label_guide(),
                'mapping_peers': peers, 'linked_names': linked_names, 'mapping_preview': True})
        try:
            with transaction.atomic():
                form.save()
        except (ValidationError, IntegrityError):
            form.add_error(None, 'Không thể lưu danh mục. Kiểm tra ngân sách/giao dịch liên quan hoặc tên bị trùng rồi thử lại.')
        else:
            messages.success(request, "Đã lưu danh mục.")
            if linked_names:
                messages.info(request, 'Nhãn này đang liên kết với các danh mục: ' + ', '.join(linked_names))
            return redirect("finance:category_list")
    return render(request, "finance/category_form.html", {
        'form': form, 'editing': category is not None, 'has_transactions': has_transactions,
        'rename_help': RENAME_HELP, 'label_guide': label_guide(),
        'mapping_peers': peers, 'linked_names': linked_names})


@login_required
@require_http_methods(["GET", "POST"])
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk, user=request.user)
    if request.method == "POST":
        try:
            category.delete()
        except ProtectedError:
            messages.error(request, "Không thể xóa danh mục đang có giao dịch hoặc ngân sách hoặc quy tắc định kỳ. Hãy xử lý các mục liên quan trước.")
        else:
            messages.success(request, "Đã xóa danh mục.")
        return redirect("finance:category_list")
    protected_recurring = category.recurring_rules.exists()
    return render(request, "finance/confirm_delete.html", {
        "object": category, "object_type": "danh mục", "cancel_url": "finance:category_list",
        "protected": category.transactions.exists() or category.budgets.exists() or protected_recurring,
        'protected_recurring': protected_recurring,
    })
