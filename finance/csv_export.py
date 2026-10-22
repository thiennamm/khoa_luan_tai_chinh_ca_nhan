"""Xuất CSV chỉ đọc, dùng lại bộ lọc của danh sách, không giới hạn số dòng."""
import csv
import unicodedata
from django.contrib.auth.decorators import login_required
from django.http import StreamingHttpResponse
from django.utils.cache import patch_vary_headers
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from .csv_import import HEADER
from .models import Transaction
from .transaction_filters import TransactionFilterForm, apply_filters
from .views import transaction_list


def protect_text(value):
    """Chỉ biến đổi bản xuất: tab trong ô quoted, không sửa DB/import.

    OWASP CSV Injection/WSTG (đọc 21/10/2026). Phát hiện cả biến thể Unicode,
    khoảng trắng và control/format ở đầu; NFKC chỉ dùng để phát hiện.
    Không bảo đảm mọi bảng tính/luồng save-reopen giữ nguyên biện pháp này.
    """
    leading_control = False
    index = 0
    while index < len(value):
        char = value[index]
        control = unicodedata.category(char) in ('Cc', 'Cf')
        if not (char.isspace() or control):
            break
        leading_control |= control
        index += 1
    first = unicodedata.normalize('NFKC', value[index:index + 1])
    risky = leading_control or first in ('=', '+', '-', '@')
    return '\t' + value if risky else value


class Echo:
    def write(self, value):
        return value


def csv_chunks(rows):
    yield '\ufeff'
    yield csv.writer(Echo(), lineterminator='\r\n').writerow(HEADER)
    writer = csv.writer(Echo(), quoting=csv.QUOTE_ALL, lineterminator='\r\n')
    for day, kind, amount, category, description in rows.values_list(
            'date', 'kind', 'amount', 'category__name', 'description').iterator(chunk_size=1000):
        yield writer.writerow([day.isoformat(), kind, format(amount, '.0f'),
                               protect_text(category), protect_text(description)])


@login_required
@require_http_methods(['GET'])
@never_cache
def transaction_export(request):
    form = TransactionFilterForm(request.GET, user=request.user)
    if not form.is_valid():
        response = transaction_list(request)
        response.status_code = 400
        return response
    rows = apply_filters(Transaction.objects.filter(user=request.user), form.cleaned_data)
    if form.cleaned_data['period'] == 'month':
        period = form.cleaned_data['month_start'].strftime('%Y%m')
    else:
        period = f"{form.cleaned_data['start']:%Y%m%d}-{form.cleaned_data['end']:%Y%m%d}"
    response = StreamingHttpResponse(csv_chunks(rows), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="transactions-{period}.csv"'
    response['X-Content-Type-Options'] = 'nosniff'
    patch_vary_headers(response, ['Cookie'])
    return response
