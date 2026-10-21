from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import OperationalError
from django.http import Http404, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .coverage import change_month_status, monthly_history, review_month
from .coverage_calendar import current_month
from .forms import CoverageConfirmationForm, CoverageStatusForm, CoverageYearForm
from .models import MonthlyCoverage


def parse_month(year, month):
    try:
        return date(year, month, 1)
    except ValueError:
        raise Http404('Tháng không hợp lệ.') from None


@login_required
@require_http_methods(['GET'])
@never_cache
def history(request):
    default_year = (current_month() - timedelta(days=1)).year
    form = CoverageYearForm({'year': request.GET.get('year', default_year)})
    valid = form.is_valid()
    year = form.cleaned_data['year'] if valid else default_year
    rows = monthly_history(request.user, date(year, 1, 1), date(year, 12, 1))
    return render(request, 'finance/monthly_history.html', {'year_form': form, 'year': year, 'rows': rows})


@login_required
@require_http_methods(['GET', 'POST'])
@never_cache
def confirm(request, year, month):
    target = parse_month(year, month)
    try:
        snapshot = review_month(request.user, target)
    except ValidationError as exc:
        return render(request, 'finance/coverage_confirm.html', {'month': target, 'notice': ' '.join(exc.messages)}, status=400)
    form = CoverageConfirmationForm(request.POST if request.method == 'POST' else None,
                                    initial={'review_token': snapshot['review_token']})
    if request.method == 'POST' and form.is_valid():
        try:
            change_month_status(request.user, target, MonthlyCoverage.Status.COMPLETE,
                review_token=form.cleaned_data['review_token'],
                confirm_no_expense=form.cleaned_data['confirm_no_expense'])
        except ValidationError as exc:
            form.add_error(None, ' '.join(exc.messages))
        except OperationalError:
            form.add_error(None, 'Đang có thao tác khác. Hãy mở lại trang xác nhận rồi thử lại.')
        else:
            messages.success(request, 'Đã ghi nhận xác nhận đầy đủ của bạn.')
            return redirect(f"{reverse('finance:monthly_history')}?year={year}")
    return render(request, 'finance/coverage_confirm.html', {'month': target, 'snapshot': snapshot, 'form': form})


@login_required
@require_http_methods(['POST'])
@never_cache
def change_status(request, year, month):
    target = parse_month(year, month)
    form = CoverageStatusForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest('Trạng thái không hợp lệ. Hãy quay lại Lịch sử ghi chép.')
    try:
        change_month_status(request.user, target, form.cleaned_data['status'])
    except (ValidationError, OperationalError):
        messages.error(request, 'Chưa cập nhật được trạng thái. Vui lòng kiểm tra tháng và thử lại.')
    else:
        messages.success(request, 'Đã cập nhật trạng thái ghi chép.')
    return redirect(f"{reverse('finance:monthly_history')}?year={year}")
