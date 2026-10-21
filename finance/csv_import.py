"""Kiểm tra CSV và xác nhận nguyên tử; không ML, không sửa dữ liệu lỗi."""
import csv
import hashlib
import io
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Category, CsvImportBatch, CsvImportReceipt, Kind, Transaction

HEADER = ['date', 'kind', 'amount', 'category', 'description']
MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 5000
PREVIEW_ROWS = 20
MAX_MESSAGES = 100
TTL = timedelta(minutes=30)


@dataclass
class Inspection:
    rows: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    count: int = 0
    income: Decimal = Decimal('0')
    expense: Decimal = Decimal('0')

    def error(self, line, message):
        self.error_count += 1
        if len(self.errors) < MAX_MESSAGES:
            self.errors.append({'line': line, 'message': message})

    def warn(self, line, message):
        self.warning_count += 1
        if len(self.warnings) < MAX_MESSAGES:
            self.warnings.append({'line': line, 'message': message})

    @property
    def sample(self):
        return self.rows[:PREVIEW_ROWS]

    @property
    def valid(self):
        return self.count > 0 and not self.error_count


def row_key(row):
    return (row['date'], row['kind'], row['amount'], row['category_id'], row['description'])


def inspect_csv(raw, user):
    result = Inspection()
    if len(raw) > MAX_BYTES:
        result.error(1, 'Tệp vượt giới hạn 2 MiB (2.097.152 byte).')
        return result
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        result.error(1, 'Không đọc được UTF-8. Hãy lưu tệp ở UTF-8 hoặc UTF-8 có BOM.')
        return result
    if '\x00' in text:
        result.error(1, 'Tệp chứa byte NUL; không phải nội dung CSV hợp lệ cho biểu mẫu này.')
        return result
    reader = csv.reader(io.StringIO(text, newline=''), strict=True)
    categories = defaultdict(list)
    for category in Category.objects.filter(user=user):
        categories[(category.kind, category.name.casefold())].append(category)
    seen = {}
    previous_end = 0
    try:
        if next(reader, None) != HEADER:
            result.error(1, 'Header phải đúng thứ tự: date,kind,amount,category,description. Không chấp nhận cột khác, kể cả user_id.')
            return result
        previous_end = reader.line_num
        for values in reader:
            line = previous_end + 1
            previous_end = reader.line_num
            result.count += 1
            if result.count > MAX_ROWS:
                result.error(line, 'Vượt giới hạn 5.000 giao dịch; hãy chia tệp thành các phần nhỏ hơn.')
                break
            if len(values) != len(HEADER):
                result.error(line, 'Mỗi giao dịch phải có đúng 5 cột, kể cả description để trống.')
                continue
            day, kind, amount, category_name, description = values
            problems = []
            parsed_date = None
            parsed_amount = None
            if not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', day):
                problems.append('Ngày phải theo YYYY-MM-DD.')
            else:
                try:
                    parsed_date = date.fromisoformat(day)
                except ValueError:
                    problems.append('Ngày không tồn tại.')
            if kind not in Kind.values:
                problems.append('Loại chỉ nhận income hoặc expense.')
            if not re.fullmatch(r'[0-9]+', amount) or len(amount.lstrip('0')) > 15:
                problems.append('Số tiền phải là số nguyên VND dương, tối đa 15 chữ số, không có dấu phân cách.')
            else:
                parsed_amount = Decimal(amount)
                if parsed_amount <= 0:
                    problems.append('Số tiền phải lớn hơn 0.')
            matches = categories.get((kind, category_name.casefold()), [])
            if not matches:
                problems.append('Không tìm thấy tên danh mục của bạn đúng loại thu/chi; hãy sửa CSV hoặc tạo danh mục trước.')
            elif len(matches) != 1:
                problems.append('Tên danh mục không xác định duy nhất; hãy đổi tên danh mục/CSV để phân biệt, không chọn ngầm.')
            if len(description) > Transaction._meta.get_field('description').max_length:
                problems.append('Mô tả vượt giới hạn 500 ký tự.')
            if problems:
                result.error(line, ' '.join(problems))
                continue
            category = matches[0]
            record = Transaction(user=user, category=category, date=parsed_date, kind=kind,
                                 amount=parsed_amount, description=description)
            try:
                # FK đã được đối chiếu theo user ở trên; không truy vấn 5.000 lần.
                record.clean_fields(exclude=['user', 'category'])
                record.clean()
            except ValidationError:
                result.error(line, 'Giao dịch không đáp ứng quy tắc dữ liệu của website.')
                continue
            row = {'line': line, 'date': parsed_date, 'kind': kind, 'amount': parsed_amount,
                   'category_id': category.pk, 'category': category.name, 'description': description}
            key = row_key(row)
            if key in seen:
                result.warn(line, f'Giống giao dịch ở dòng {seen[key]} trong tệp. Vẫn giữ cả hai nếu bạn xác nhận.')
            else:
                seen[key] = line
            result.rows.append(row)
            if kind == Kind.INCOME:
                result.income += parsed_amount
            else:
                result.expense += parsed_amount
    except csv.Error:
        result.error(max(1, previous_end + 1), 'Cú pháp CSV không hợp lệ (dấu nháy, cột hoặc ô quá dài).')
    if not result.count and not result.error_count:
        result.error(reader.line_num + 1, 'Tệp chỉ có header, chưa có giao dịch để nhập.')
    if result.rows:
        dates = [r['date'] for r in result.rows]
        existing = set()
        for values in Transaction.objects.filter(user=user, date__range=(min(dates), max(dates))).values_list(
                'date', 'kind', 'amount', 'category_id', 'description').iterator():
            if values in seen:
                existing.add(values)
        for row in result.rows:
            if row_key(row) in existing:
                result.warn(row['line'], 'Giống một giao dịch đã có trong tài khoản. Không tự xóa/gộp; hãy kiểm tra trước khi xác nhận.')
    return result


class ImportProblem(Exception):
    """Chỉ thông báo chung, không chứa mô tả hoặc nội dung tệp."""


def cleanup_batches(user=None):
    query = CsvImportBatch.objects.filter(expires_at__lte=timezone.now())
    if user is not None:
        query = query.filter(user=user)
    return query.delete()[1].get('finance.CsvImportBatch', 0)


def stage_csv(raw, user, inspection):
    if not inspection.valid:
        raise ImportProblem('Tệp còn lỗi; chưa thể tạo bản xem trước để xác nhận.')
    sha = hashlib.sha256(raw).hexdigest()
    if CsvImportReceipt.objects.filter(user=user, sha256=sha).exists():
        raise ImportProblem('Tệp có cùng SHA-256 đã được nhập thành công trong tài khoản này; đã chặn nhập lại.')
    return CsvImportBatch.objects.create(user=user, raw=raw, sha256=sha,
        category_bindings=[row['category_id'] for row in inspection.rows], expires_at=timezone.now() + TTL)


def inspect_batch(batch, user):
    if batch.user_id != user.pk:
        raise ImportProblem('Lô nhập không thuộc tài khoản của bạn.')
    if batch.expires_at <= timezone.now():
        raise ImportProblem('Bản xem trước đã hết hạn sau 30 phút. Vui lòng tải lại tệp.')
    raw = bytes(batch.raw)
    if hashlib.sha256(raw).hexdigest() != batch.sha256:
        raise ImportProblem('Dữ liệu tạm không khớp hash; hãy tải lại tệp.')
    result = inspect_csv(raw, user)
    if result.valid and [r['category_id'] for r in result.rows] != batch.category_bindings:
        result.error(1, 'Danh mục đã thay đổi so với lúc tải tệp. Hãy tải lại để xem trước ánh xạ mới.')
    return result


def confirm_batch(batch_id, user):
    with transaction.atomic():
        # UPDATE là câu lệnh đầu tiên trong transaction: khóa ghi thật trên SQLite.
        # Không dựa vào select_for_update (SQLite không hỗ trợ khóa hàng).
        claimed = CsvImportBatch.objects.filter(pk=batch_id, user=user, status='pending',
            expires_at__gt=timezone.now()).update(status='processing')
        if not claimed:
            raise ImportProblem('Lô nhập đã xác nhận, đang được xử lý hoặc đã hết hạn. Không nhập thêm lần nữa.')
        batch = CsvImportBatch.objects.get(pk=batch_id, user=user)
        if CsvImportReceipt.objects.filter(user=user, sha256=batch.sha256).exists():
            raise ImportProblem('Tệp có cùng SHA-256 đã nhập thành công; đã chặn nhập lại.')
        inspection = inspect_batch(batch, user)
        if not inspection.valid:
            raise ImportProblem('Dữ liệu hoặc danh mục đã thay đổi/không còn hợp lệ. Chưa nhập giao dịch nào; mở lại bản xem trước để xem lỗi.')
        CsvImportReceipt.objects.create(user=user, sha256=batch.sha256, batch=batch,
            transaction_count=len(inspection.rows))
        Transaction.objects.bulk_create([
            Transaction(user=user, category_id=row['category_id'], kind=row['kind'], amount=row['amount'],
                        date=row['date'], description=row['description'])
            for row in inspection.rows
        ], batch_size=100)
        batch.status = 'completed'
        batch.raw = b''
        batch.category_bindings = []
        batch.save(update_fields=['status', 'raw', 'category_bindings'])
        return len(inspection.rows)
