"""Conservative rule parser for prefilling; never saves or runs inference."""
import re
import unicodedata
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.utils import timezone
from .models import Transaction

MAX_LENGTH = Transaction._meta.get_field('description').max_length
MAX_AMOUNT = Decimal('9' * Transaction._meta.get_field('amount').max_digits)
DATE_TOKEN = re.compile(r'(?<!\w)(hôm nay|hôm qua|[0-9]{1,4}[/.-][0-9]{1,2}(?:[/.-][0-9]{1,4})?)(?!\w)', re.I)
UNSUPPORTED_DATE = re.compile(r'\b(ngày mai|hôm kia|tuần trước|tuần sau|tháng trước|tháng sau)\b', re.I)
MONEY_TOKEN = re.compile(
    r'(?<![\w.,+−–—-])(?P<number>[+−–—-]?[ \t]*[0-9][0-9.,]*(?:[ \t]+[0-9][0-9.,]*)*)'
    r'[ \t]*(?P<unit>nghìn|triệu|vnd|[kđ₫])(?!\w)', re.I)
MONEY_CANDIDATE = re.compile(r'[0-9][0-9.,]*(?:[ \t]+[0-9][0-9.,]*)*[ \t]*(?:nghìn|triệu|vnd|[kđ₫])(?!\w)', re.I)
KIND_PREFIX = re.compile(r'^\s*(thu(?: nhập)?|chi(?: tiêu)?)\s*:\s*', re.I)


class QuickEntryError(ValueError):
    def __init__(self, errors):
        self.errors = errors
        super().__init__('Quick entry rejected')  # No private input in exceptions/logs.


def parse_entry(raw):
    if not isinstance(raw, str) or not raw.strip():
        raise QuickEntryError(['Nhập một câu để điền trước biểu mẫu.'])
    if len(raw) > MAX_LENGTH:
        raise QuickEntryError([f'Câu nhập nhanh tối đa {MAX_LENGTH} ký tự.'])
    if '\n' in raw or '\r' in raw:
        raise QuickEntryError(['Mỗi lần chỉ nhập một câu cho một giao dịch, không xuống dòng.'])
    text = unicodedata.normalize('NFC', raw).strip()
    today = timezone.localdate()
    errors, warnings, spans = [], [], []
    dates = list(DATE_TOKEN.finditer(text))
    if len(re.findall(r'(?<!\w)(?:thu(?: nhập)?|chi(?: tiêu)?)\s*:', text, re.I)) > 1:
        errors.append('Có nhiều dấu hiệu Thu:/Chi:; hãy tách thành một giao dịch mỗi lần.')
    if UNSUPPORTED_DATE.search(text):
        errors.append('Ngày tương đối này chưa được hỗ trợ. Dùng hôm nay, hôm qua hoặc dd/mm/yyyy.')
    if len(dates) > 1:
        errors.append('Có nhiều ngày; hãy để đúng một ngày hoặc sửa bằng biểu mẫu thường.')
    chosen_date = today
    for match in dates:
        token = match.group().casefold()
        try:
            if token == 'hôm nay':
                chosen_date = today
            elif token == 'hôm qua':
                chosen_date = today - timedelta(days=1)
            elif re.fullmatch(r'[0-9]{2}/[0-9]{2}/[0-9]{4}', token):
                day, month, year = map(int, token.split('/'))
                chosen_date = date(year, month, day)
            else:
                raise ValueError
        except (ValueError, OverflowError):
            errors.append('Ngày không hợp lệ hoặc chưa đúng dd/mm/yyyy. Không tự sửa ngày.')
        spans.append(match.span())
    masked = list(text)
    for start, end in spans:
        masked[start:end] = ' ' * (end-start)
    money = list(MONEY_TOKEN.finditer(''.join(masked)))
    if len(list(MONEY_CANDIDATE.finditer(''.join(masked)))) != len(money):
        errors.append('Có số kèm đơn vị nhưng định dạng chưa hỗ trợ. Hãy tách rõ số tiền; không tự chọn một phần câu.')
    amount = None
    if len(money) != 1:
        errors.append('Có nhiều số tiền có đơn vị; hãy để đúng một số tiền.' if money else
                      'Chưa nhận diện được tiền. Dùng 45k, 45 nghìn, 1,5 triệu hoặc 45000đ.')
    else:
        match = money[0]
        number, unit = match['number'].strip(), match['unit'].casefold()
        try:
            if not re.fullmatch(r'[0-9]+(?:,[0-9]+)?', number):
                raise InvalidOperation
            if unit in ('đ', '₫', 'vnd') and ',' in number:
                raise InvalidOperation
            multiplier = Decimal('1000') if unit in ('k', 'nghìn') else (
                Decimal('1000000') if unit == 'triệu' else Decimal('1'))
            # Bound input digits before multiplication, including very long decimal strings.
            if len(number.replace(',', '').lstrip('0')) > 24:
                raise InvalidOperation
            amount = Decimal(number.replace(',', '.')) * multiplier
            if amount != amount.to_integral_value() or not Decimal('1') <= amount <= MAX_AMOUNT:
                raise InvalidOperation
        except InvalidOperation:
            errors.append('Tiền phải là số nguyên VND dương trong giới hạn 999999999999999; '
                          'không dùng dấu chấm, phân cách hàng nghìn hoặc dấu âm/dương.')
        spans.append(match.span())
    # Explicit unsupported currency is not silently treated as a VND transaction.
    if (re.search(r'\b(usd|eur|dollars?|euro|tr|ngàn)\b|[$€£¥]', ''.join(masked), re.I)
            or re.search(r'[0-9][0-9.,]*[ \t]*(?:tỷ|tỉ|đồng|đô(?:[ \t]+la)?|jpy|gbp|cny)(?!\w)',
                         ''.join(masked), re.I)):
        errors.append('Đơn vị này chưa được hỗ trợ; chỉ nhập VND với k, nghìn, triệu, đ, ₫ hoặc VND.')
    if errors:
        raise QuickEntryError(list(dict.fromkeys(errors)))
    kind = ''
    prefix = KIND_PREFIX.match(text)
    if prefix:
        kind = 'income' if prefix[1].casefold().startswith('thu') else 'expense'
        spans.append(prefix.span())
    else:
        warnings.append('Chưa xác định loại thu/chi. Hãy tự chọn; không suy ra từ nội dung mua hàng hay tiền vào.')
    remaining = list(text)
    for start, end in spans:
        remaining[start:end] = ' ' * (end-start)
    description = ' '.join(''.join(remaining).split())
    if not dates:
        warnings.append('Không có ngày: dùng hôm nay theo giờ Việt Nam, ' + today.strftime('%d/%m/%Y') + '.')
    if chosen_date > today:
        warnings.append('Ngày đã nhận diện ở tương lai; hãy kiểm tra trước khi lưu. Chính sách ngày của biểu mẫu vẫn giữ nguyên.')
    if re.search(r'[0-9]', description):
        warnings.append('Mô tả còn số chưa diễn giải (ví dụ mã hóa đơn/số điện thoại); chúng được giữ nguyên, không tính thành tiền.')
    if not description:
        warnings.append('Mô tả sau xử lý đang trống; bạn có thể bổ sung trong biểu mẫu.')
    warnings.append('Danh mục sẽ để trống để bạn tự chọn hoặc chủ động yêu cầu gợi ý ML.')
    return {'status': 'ok', 'fields': {'amount': format(amount, '.0f'), 'date': chosen_date.isoformat(),
            'kind': kind, 'description': description}, 'date_defaulted': not dates, 'warnings': warnings}
