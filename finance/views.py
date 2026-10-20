from datetime import date
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .forms import CategoryForm, MonthForm, SignUpForm, TransactionForm
from .models import Category, Transaction
from .services import monthly_totals


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
        user = form.save()
        login(request, user)
        messages.success(request, "Đăng ký thành công. Hãy tạo danh mục đầu tiên của bạn.")
        return redirect("finance:dashboard")
    return render(request, "registration/signup.html", {"form": form})


@login_required
@require_http_methods(["GET"])
def dashboard(request):
    context = month_context(request)
    rows = Transaction.objects.filter(user=request.user, date__gte=context["start"], date__lt=context["end"])
    context.update(monthly_totals(request.user, context["start"], context["end"]))
    context.update({"recent_transactions": rows.select_related("category")[:5], "transaction_count": rows.count()})
    return render(request, "finance/dashboard.html", context)


@login_required
@require_http_methods(["GET"])
def transaction_list(request):
    context = month_context(request)
    rows = Transaction.objects.filter(user=request.user, date__gte=context["start"], date__lt=context["end"]).select_related("category")
    context["page_obj"] = Paginator(rows, 20).get_page(request.GET.get("page"))
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
        form.save()
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
            messages.error(request, "Không thể xóa danh mục đang có giao dịch. Hãy chuyển hoặc xóa các giao dịch liên quan trước.")
        else:
            messages.success(request, "Đã xóa danh mục.")
        return redirect("finance:category_list")
    return render(request, "finance/confirm_delete.html", {
        "object": category, "object_type": "danh mục", "cancel_url": "finance:category_list",
        "protected": category.transactions.exists(),
    })
